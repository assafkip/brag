#!/usr/bin/env python3
"""Turn ffmpeg's first-pass loudnorm JSON (read from stdin, as printed to stderr) into the second-pass arguments.

  ffmpeg -i a.wav -af loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json -f null - 2>&1 | python3 loudnorm_args.py

Prints: measured_I=..:measured_TP=..:measured_LRA=..:measured_thresh=..:offset=..
Used by mux.sh so the final pass can run with linear=true and land on the target.
"""
import json
import re
import sys

text = sys.stdin.read()
found = re.search(r'\{[^{}]*"input_i"[^{}]*\}', text, re.S)
if not found:
    sys.exit("loudnorm_args: no loudnorm JSON on stdin (does the soundtrack have audio?)")
m = json.loads(found.group(0))
print("measured_I=%s:measured_TP=%s:measured_LRA=%s:measured_thresh=%s:offset=%s"
      % (m["input_i"], m["input_tp"], m["input_lra"], m["input_thresh"], m["target_offset"]))
