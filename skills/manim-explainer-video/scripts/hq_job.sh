#!/bin/bash
# Usage: bash hq_job.sh <file> "S01 S02"  -> 1080p30 renders (HQ_<Scene>.mp4), progress in hq_<file>.txt
# Run detached and poll hq_<file>.txt for DONE. Each scene's partial movie files are removed after it renders.
f=$1
: > hq_$f.txt
for s in $2; do
  if manim -qh --frame_rate 30 --disable_caching -o HQ_$s $f.py $s > logs_$s.txt 2>&1; then echo "OK $s $(date +%T)" >> hq_$f.txt
  else echo "FAIL $s (see logs_$s.txt)" >> hq_$f.txt; fi
  rm -rf media/videos/$f/1080p30/partial_movie_files/$s
done
echo DONE >> hq_$f.txt
