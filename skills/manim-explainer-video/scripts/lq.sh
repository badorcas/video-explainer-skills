#!/bin/bash
# Usage: bash lq.sh <file> "S01 S02"  -> 480p15 renders + layout QA (qa/<Scene>.txt); summary in lq_<file>.txt
# Run detached and poll lq_<file>.txt for DONE.
export QA=1
f=$1; shift
: > lq_$f.txt
for s in $1; do
  rm -f qa/$s.late.txt
  if manim -ql --disable_caching -o $s $f.py $s > lqlog_$s.txt 2>&1; then
    echo "OK $s  qa: $(wc -l < qa/$s.txt 2>/dev/null || echo '?') issues (qa/$s.txt)" >> lq_$f.txt
  else echo "FAIL $s (see lqlog_$s.txt)" >> lq_$f.txt; fi
done
echo DONE >> lq_$f.txt
