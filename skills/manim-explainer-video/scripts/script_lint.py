"""Check a narration script before voicing it: does it explain, or does it read out numbers?

  python3 script_lint.py narration.txt [--wpm 150]

Every CHECK is advisory: it points at a passage to listen to, not a target to satisfy. Joining sentences
with commas to pass `short` trades slogans for rambling.

Same script format as voice.py ("## Sxx Title" scenes, [PAUSE n], "# " comments). Per scene it counts spoken
numbers (a run like "six hundred and seventeen" or "point seven four" is one number) per minute of speech,
estimated from the word count, and causal links ("because", "so", "which means", ...). It prints a table and
CHECK lines:
  numbers   a scene says more than 12 numbers a minute, or the whole script more than 9: the viewer is
            being read results instead of shown why. Keep the numbers the lesson needs; spend the time on
            the mechanism (see review-checklist.md S1).
  no-why    a scene says 4+ numbers with no causal link at all.
  short     a scene's sentences average under 13 words: it reads as slogans, not spoken explanation
            (see references/script-writing.md section 4; human explainers run 18 to 28).
  fragments more than 12% of sentences have under 6 words.
  arith     arithmetic read aloud ("plus", "times", "divided by", "equals" next to a number): say the result.
  stage     narrator stage directions ("keep your answer", "remember that", "let's build").
  long-sent a sentence over 55 words: likely overloaded.
Calibrated on caption transcripts of 3Blue1Brown (Fourier transform 25 words a sentence, 4% under 6 words,
3 numbers a minute; convolution 28, 1%, 5), Marshall Bruner (phased-array windows 20, 8%, 2) and Khan
Academy (Laplace 12, 13%, 4). The two rejected Video 5 and Video 3 scripts ran 8 to 11 words, 18 to 42%.
  stray     spoken text before the first scene, or a malformed [PAUSE] line (it would be voiced).
  long-para a paragraph over 90 words (about 35 s of voice): split it so the script reads well and the voice breathes.
Grammar checks (advisory; need spaCy, and are skipped with one NOTE line when it is missing). The Nix shell
(skill/flake.nix) provides spacy and en_core_web_sm; outside it: pip install spacy &&
python3 -m spacy download en_core_web_sm. Sentences are taken after dropping [PAUSE x] tags and # lines.
  fragment     a sentence with no finite verb and no imperative root (no token with VerbForm=Fin).
  fragment-ok? the same, but a one or two word interjection ("Okay.") or a short question, listed apart to skim.
  tense-shift  review prompt, not an error: (a) a sentence whose main verb tense (Past or Pres) differs from its
               paragraph's majority (paragraphs of 4+ tensed sentences, 75%+ agreeing); (b) a present-simple
               "we" sentence with a design-decision verb (bias, choose, set, pick, size, mount, put, place, give,
               make) in a paragraph that otherwise narrates in the past: likely a past decision stated as a habit
               ("For this craft, we bias them away from zero speed.": say "we biased" or "we have biased").
  vague-ref    a sentence opening with bare It/That/This/These/Those followed by a verb or 's: the pronoun is
               not followed by a noun. Prints the previous sentence's subject as context. Name the thing.
Not spaCy-based, always run:
  generic      vague value words where a quantity or mechanism belongs (a lot, very, really, quite, pretty,
               kind of, somehow, something, things, stuff, the trouble, hurts, worse, better, matters, isn't
               quite). Prints the sentence.
Calibrated on two scripts: one the user called "just blabs numbers" (13 a minute overall, 6 of 10 scenes over 12)
and one that explains by mechanism (6 a minute; only its quiz scene, at 16, goes over)."""
import re, sys
from collections import Counter

UNITS = ("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen "
         "seventeen eighteen nineteen twenty thirty forty fifty sixty seventy eighty ninety hundred thousand "
         "million billion point half quarter").split()
WHY = re.compile(r"\b(because|since|so|which means|that means|that's why|this is why|the reason|therefore|"
                 r"thanks to|due to|causes?|makes?|why)\b")

args = sys.argv[1:]
wpm = float(args[args.index("--wpm") + 1]) if "--wpm" in args else 150.0
path = [a for a in args if not a.startswith("--") and not re.fullmatch(r"[\d.]+", a)][0]

scenes, cur, stray, pause = [], None, [], 0.0
for raw in open(path):
    line = raw.strip()
    m = re.fullmatch(r"\[PAUSE ([\d.]+)\]", line)
    if m:
        pause += float(m.group(1))
    elif "[" in line and not line.startswith("#"):
        stray.append(f"CHECK stray: bracket in spoken line: {line[:60]}")
    if cur is None and line and not line.startswith("#") and not line.startswith("## "):
        stray.append(f"CHECK stray: spoken text before the first scene: {line[:60]}")
    if line.startswith("## "):
        sid, title = (line[3:].split(" ", 1) + [""])[:2]
        cur = {"id": sid, "title": title, "text": [], "paras": [""]}
        scenes.append(cur)
    elif cur is not None and line and not line.startswith("# ") and line != "#" \
            and not re.fullmatch(r"\[PAUSE [\d.]+\]", line):
        cur["text"].append(line)
        cur["paras"][-1] += " " + line
    elif cur is not None and not line and cur["paras"][-1]:
        cur["paras"].append("")


def count_numbers(text):
    """Spoken numbers in text; a run of number words ("six hundred and seventeen") counts once."""
    toks = re.findall(r"[a-z]+|\d[\d,.]*", text.lower().replace("-", " "))
    n, run = 0, False
    for i, t in enumerate(toks):
        inner_and = t == "and" and run and i + 1 < len(toks) and toks[i + 1] in UNITS
        num = t[0].isdigit() or t in UNITS or inner_and
        n += num and not run
        run = num
    return n


tot_n = tot_w = 0
checks, generic = [], []
ARITH = re.compile(r"\b(plus|minus|times|divided by|equals|squared)\b")
STAGE = re.compile(r"\b(keep your answer|remember that|let's build|pause here)\b")
NUMW = re.compile(r"\d|\b(" + "|".join(UNITS) + r")\b")


def sentences(text):
    return [x for x in re.split(r"(?<=[.?!])\s+", text) if x.strip()]


GENERIC = re.compile(r"\b(a lot|very|really|quite|pretty|kind of|somehow|something|things|stuff|the trouble|"
                     r"hurts?|worse|better|matters?|isn't quite|is not quite)\b", re.I)
DECISION = {"bias", "choose", "set", "pick", "size", "mount", "put", "place", "give", "make"}
VAGUE = {"it", "that", "this", "these", "those"}
IMPERATIVES = set("plot look watch notice imagine picture take compare consider think see ask say try add subtract "
                  "divide multiply keep let use pick choose draw set start stop pause check run read listen note "
                  "remember put give make find count".split())
IDIOM = re.compile(r"it (turns out|comes down|takes|seems|appears|helps to|is (worth|time|clear|easy|hard|important)|"
                   r"'s (worth|time|clear|easy|hard|important|the \w+ that)|looks like|means that|ends up)")
HEDGE = {"if", "when", "say", "suppose", "imagine", "whenever", "unless", "once", "while"}


def clean(text):
    return re.sub(r"\s+", " ", re.sub(r"\[PAUSE[^\]]*\]", " ", text)).strip()


def load_nlp():
    try:
        import spacy
        return spacy.load("en_core_web_sm", disable=["ner"])
    except Exception:
        return None


def main_tense(sent):
    """'Past', 'Pres' or None (modal, perfect, future, imperative, no finite verb) for a spaCy sentence."""
    root = sent.root
    if not is_fin(root):
        auxs = [c for c in root.children if c.dep_ in ("aux", "auxpass") and is_fin(c)]
        if not auxs or any(a.lower_ in ("will", "would", "can", "could", "should", "may", "might", "must", "shall")
                           for a in auxs):
            return None
        if auxs[0].lemma_ == "have" and "Part" in root.morph.get("VerbForm"):
            return None  # present perfect says the thing is done: neutral
        t = auxs[0].morph.get("Tense")
    else:
                t = root.morph.get("Tense")
    return t[0] if t and t[0] in ("Past", "Pres") else None


def is_fin(t):
    return "Fin" in t.morph.get("VerbForm") or t.tag_ in ("MD", "VBZ", "VBP", "VBD")


NOT_BEFORE_VERB = {"the", "a", "an", "of", "and", "or", "to", "in", "on", "at", "for", "by", "with", "per"}


def verb_plausible(sent, nlp):
    """The small model tags many verbs as plural nouns ("the delay costs under two degrees") and leading imperatives
    as nouns ("Then plot bus angle"). Second opinion: put "will" before one NNS token (or "Please" first) and see
    whether a verb with a subject (or an imperative root) appears."""
    toks = list(sent)
    words = [t.text_with_ws for t in toks]
    for i, t in enumerate(toks):
        if t.tag_ in ("NNS", "NN", "VBP") and i > 1 and t.is_alpha and toks[i - 1].lower_ not in NOT_BEFORE_VERB \
                and toks[i - 1].tag_ not in ("DT", "JJ", "IN", "PRP$", "CD"):
            stem = t.lemma_.lower() if t.tag_ == "NNS" else t.lower_
            d = nlp("".join(words[:i]) + "will " + stem + " " + "".join(words[i + 1:]))
            for v in d:
                if v.tag_ == "VB" and v.i == i + 1 and (v.dep_ in ("ROOT", "conj") or any(c.dep_ == "nsubj" for c in v.children)):
                    return True
    first = [t for t in toks if t.pos_ not in ("ADV", "CCONJ", "PUNCT", "INTJ")][:1]
    if first and first[0].tag_ in ("NN", "VBP", "NNS") and first[0].lemma_.lower() in IMPERATIVES:
        return True
    return False


def finite_or_imperative(sent, nlp=None):
    if any(is_fin(t) for t in sent):
        return True
    if any(t.tag_ == "VB" and any(c.dep_ == "nsubj" for c in t.children) and not any(c.dep_ in ("aux", "auxpass", "mark") for c in t.children)
           for t in sent):
        return True  # the small model tags bare plural-subject verbs ("wheels also add") VB
    if nlp is not None and len(sent.text.split()) >= 4 and verb_plausible(sent, nlp):
        return True
    r = sent.root
    if r.lemma_ == "let" or sent[0].lower_ == "let":
        return True
    return r.pos_ in ("VERB", "AUX") and r.tag_ == "VB" and not any(c.dep_ in ("nsubj", "nsubjpass") for c in r.children)


def subject_of(sent):
    for t in sent:
        if t.dep_ in ("nsubj", "nsubjpass") and t.pos_ in ("NOUN", "PROPN"):
            return " ".join(w.text for w in t.subtree if w.i <= t.i)
    nouns = [t for t in sent if t.pos_ in ("NOUN", "PROPN")]
    return nouns[0].text if nouns else "?"


def grammar(scenes, nlp):
    out = {"fragment": [], "fragment-ok?": [], "tense-shift": [], "vague-ref": []}
    for s in scenes:
        prev = None
        for para in s["paras"]:
            para = clean(para)
            if not para:
                continue
            sents = list(nlp(para).sents)
            tenses = [main_tense(x) for x in sents]
            counted = [t for t in tenses if t]
            maj, share = (None, 0)
            if len(counted) >= 3:
                maj, n = Counter(counted).most_common(1)[0]
                share = n / len(counted)
            has_past = "Past" in counted
            for x, t in zip(sents, tenses):
                txt = x.text.strip()
                words = [w for w in x if w.is_alpha]
                if not words:
                    continue
                if not finite_or_imperative(x, nlp):
                    short = any(w.pos_ == "INTJ" for w in words) or (len(words) == 1) \
                        or (txt.endswith("?") and len(words) <= 6)
                    out["fragment-ok?" if short else "fragment"].append(f"{s['id']}: {txt[:120]}")
                ambiguous = t == "Past" and x.root.lower_ in ("put", "set", "cut", "let", "read", "hit", "shut")
                anchored = re.search(r"\b(last time|earlier|before|previously|already|so far|just)\b", txt.lower())
                if maj and share >= 0.66 and t and t != maj and not ambiguous and not anchored and not txt.endswith("?"):
                    out["tense-shift"].append(f"{s['id']}: review: {t.lower()} among {maj.lower()}: {txt[:100]}")
                r = x.root
                subj = [c for c in r.children if c.dep_ == "nsubj" and c.lower_ in ("we", "i")]
                if subj and t == "Pres" and r.lemma_ in DECISION and not txt.endswith("?") \
                        and not any(w.lower_ in HEDGE for w in x) and not any(c.dep_ == "neg" for c in r.children):
                    out["tense-shift"].append(f"{s['id']}: review: present simple decision verb, past meant?: {txt[:100]}")
                toks = [w for w in x if not w.is_punct]
                i = 0
                while i < len(toks) - 1 and toks[i].lower_ in ("and", "but", "so", "now", "then"):
                    i += 1
                if toks[i].lower_ in VAGUE and toks[i].dep_ not in ("expl", "det") and i + 1 < len(toks) \
                        and not IDIOM.match(" ".join(w.lower_ for w in toks[i:i + 6])):
                    nx = toks[i + 1]
                    j = i + 1
                    while j < len(toks) - 1 and toks[j].pos_ == "ADV" and toks[j].lower_ not in ("s", "'s"):
                        j += 1
                    nx = toks[j]
                    if nx.pos_ in ("VERB", "AUX") or nx.text in ("'s", "\u2019s", "'ll", "'d"):
                        if toks[i].lower_ == "it" and nx.lemma_ in ("take", "seem", "matter", "look") and False:
                            pass
                        else:
                            out["vague-ref"].append(f"{s['id']}: {txt[:90]} [previous subject: {subject_of(prev) if prev is not None else 'none'}]")
                prev = x
    return out


print(f"{'scene':6s} {'title':30s} {'min':>5s} {'num/min':>8s} {'why':>4s} {'w/sent':>6s} {'frag':>5s}")
for s in scenes:
    text = " ".join(s["text"])
    words = len(text.split())
    if not words:
        continue
    mins = words / wpm
    n, why = count_numbers(text), len(WHY.findall(text.lower()))
    tot_n, tot_w = tot_n + n, tot_w + words
    sents = sentences(text)
    wps = words / max(1, len(sents))
    frag = sum(len(x.split()) < 6 for x in sents) / max(1, len(sents))
    print(f"{s['id']:6s} {s['title'][:30]:30s} {mins:5.1f} {n / mins:8.1f} {why:4d} {wps:6.1f} {frag:5.0%}")
    if wps < 13:
        checks.append(f"CHECK short {s['id']}: {wps:.0f} words a sentence (want 14 to 24)")
    if len(sents) >= 6 and frag > 0.12:
        checks.append(f"CHECK fragments {s['id']}: {frag:.0%} of sentences under 6 words")
    for x in sents:
        hits = {m.lower() for m in GENERIC.findall(x)}
        if re.search(r"\bthan\b", x.lower()):
            hits -= {"better", "worse"}  # a stated comparison is specific enough
        if NUMW.search(x.lower()):
            hits -= {"very", "quite", "pretty", "really"}  # the quantity is stated; the modifier only comments on it
        if re.search(r"\b(if|when|whenever|unless) something\b", x.lower()):
            hits -= {"something"}
        if hits:
            generic.append(f"CHECK generic {s['id']}: {clean(x)[:120]} [{', '.join(sorted(hits))}]")
        if ARITH.search(x.lower()) and len(NUMW.findall(x.lower())) >= 3:
            checks.append(f"CHECK arith {s['id']}: {x[:70]}")
        if len(x.split()) > 55:
            checks.append(f"CHECK long-sent {s['id']}: {len(x.split())} words: {x[:60]}")
        if STAGE.search(x.lower()):
            checks.append(f"CHECK stage {s['id']}: {x[:70]}")
    for para in s["paras"]:
        if len(para.split()) > 90:
            checks.append(f"CHECK long-para {s['id']}: {len(para.split())} words: {para[:50]}")
    if n / mins > 12:
        checks.append(f"CHECK numbers {s['id']}: {n / mins:.0f} numbers a minute (limit 12)")
    if n >= 4 and why == 0:
        checks.append(f"CHECK no-why {s['id']}: {n} numbers and no causal link")
avg = tot_n / (tot_w / wpm) if tot_w else 0
print(f"{'all':6s} {'':30s} {tot_w / wpm:5.1f} {avg:8.1f}")
print(f"speech {tot_w / wpm:.1f} min at {wpm:.0f} wpm, explicit pauses {pause:.0f} s, total about {tot_w / wpm + pause / 60:.1f} min")
nlp = load_nlp()
gram = []
if nlp is None:
    gram.append("NOTE grammar checks skipped: spaCy or en_core_web_sm not importable (see the docstring)")
else:
    res = grammar(scenes, nlp)
    for k in ("fragment", "fragment-ok?", "tense-shift", "vague-ref"):
        gram += [f"CHECK {k} {v}" for v in res[k]]
checks = stray + checks + gram + generic
if not scenes:
    checks.append("CHECK stray: no '## Sxx' scenes found")
if avg > 9:
    checks.append(f"CHECK numbers script: {avg:.0f} numbers a minute overall (limit 9)")
print("\n".join(checks) if checks else "clean")
