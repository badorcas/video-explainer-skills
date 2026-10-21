#!/bin/bash
# Blender line-art stills, then a contact sheet per output folder.
#   bash blender_stills.sh shots.py outdir [shots2.py outdir2 ...]
# Each shots script renders every shot it defines ("--shot all") and imports the helpers with
#   sys.path.insert(0, os.environ["SKILL_SCRIPTS"]); import blender_lineart as L
# Detaches by default; the log goes to $LOG (default ./blender_stills.log). Set FG=1 to run in the foreground.
# Resumable: a shot script should skip a still whose PNG already exists; blender_lineart.render() writes
# PNG and anchor JSON through temporary files renamed into place, so a killed run leaves nothing half
# written. Delete a PNG to redo it. W, H and S (samples) override 1920, 1080 and 16.
SKILL="$(cd "$(dirname "$0")/.." && pwd)"
LOG=${LOG:-$PWD/blender_stills.log}
if [ $# -lt 2 ] || [ $(( $# % 2 )) -ne 0 ]; then
  echo "usage: bash blender_stills.sh shots.py outdir [shots2.py outdir2 ...]" >&2; exit 2
fi
if [ -z "$FG" ] && [ -z "$BLENDER_STILLS_CHILD" ]; then
  BLENDER_STILLS_CHILD=1 nohup bash "$0" "$@" > "$LOG" 2>&1 < /dev/null &
  echo "detached: pid $!, log $LOG"; exit 0
fi
W=${W:-1920}; H=${H:-1080}; S=${S:-16}
export SKILL_SCRIPTS="$SKILL/scripts"
while [ $# -gt 0 ]; do
  shots=$(realpath "$1"); out=$(realpath -m "$2"); shift 2
  mkdir -p "$out"
  nix develop "$SKILL#blender" --command blender -b -P "$shots" -- --shot all --out "$out" --w $W --h $H --samples $S
  nix develop "$SKILL" --command python3 "$SKILL/scripts/contact_sheet.py" "$out" "$out/contact_sheet.png"
done
echo "ALL DONE"
