#!/bin/bash
# Usage: bash render_all.sh "file1:SceneA file1:SceneB file2:SceneC"
# Renders each scene at 1080p30 into media/videos/<file>/1080p30/HQ_<Scene>.mp4.
# Launch detached:  setsid nohup bash render_all.sh "..." >/dev/null 2>&1 </dev/null &
# Then poll progress.txt in separate tool calls (each call is capped at 300 s).
rm -f progress.txt fails.txt
for spec in $1; do
  f=${spec%%:*}; s=${spec##*:}
  manim -qh --frame_rate 30 --disable_caching -o HQ_$s $f.py $s > logs_$s.txt 2>&1 || echo "FAIL $s" >> fails.txt
  echo "$s $(date +%T)" >> progress.txt
done
echo DONE >> progress.txt
