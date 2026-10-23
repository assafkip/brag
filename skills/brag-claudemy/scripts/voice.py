#!/usr/bin/env python3
"""Narration with ElevenLabs, from a narration.txt, behind the spend gate.

  python3 voice.py --voice-id <id> [--project .] [--narration narration.txt] [--out narration]
                   [--model eleven_multilingual_v2] [--stability 0.40] [--similarity 0.75] [--style 0.20]
                   [--no-speaker-boost] [--dry-run]

narration.txt holds one sentence per block, blocks separated by a blank line. The blocks go in ONE request to the
with-timestamps endpoint (so the voice keeps its rhythm across sentences), and the character alignment that comes
back is turned into start and end seconds per sentence.

Writes <out>.mp3, <out>.sentences.json (per sentence: text, start, end; plus the character count, voice and model)
and appends the characters used to <project>/spend.log.

The key is read ONLY from the environment variable ELEVENLABS_API_KEY. It is never printed, never written, never
passed on a command line. It runs only when BRIEF.md carries an approved line for ElevenLabs under "Spend approved"
(for example: "Spend approved: up to $5 for ElevenLabs narration"). --dry-run makes no network call, spends nothing
and prints the request shape with the key masked, so it also runs without the approval and says what a live run
would do.

Voice settings are judged by ear, not derived: render one sentence, listen, change one setting, render again.
"""
import argparse
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ENDPOINT = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/with-timestamps?output_format=mp3_44100_128"
MAX_CHARS = 5000
KEY_VAR = "ELEVENLABS_API_KEY"


def read_blocks(text):
    return [re.sub(r"\s+", " ", b).strip() for b in re.split(r"\n\s*\n", text) if b.strip()]


def approved(brief_text):
    """True if BRIEF.md has an approved line that mentions ElevenLabs, either as 'Spend approved: ...' on one line
    or as lines under a 'Spend approved' heading. 'none' is not an approval."""
    lines = brief_text.splitlines()
    for i, line in enumerate(lines):
        m = re.match(r"^\W*spend approved\W*:?\s*(.*)$", line.strip(), re.I)
        if not m:
            continue
        block = [m.group(1)]
        if line.lstrip().startswith("#"):
            for nxt in lines[i + 1:]:
                if nxt.startswith("#"):
                    break
                block.append(nxt)
        for text in block:
            t = text.strip()
            if t and not re.match(r"^none\b", t, re.I) and "elevenlabs" in t.lower():
                return True
    return False


def build_request(blocks, voice_id, model, stability, similarity, style, boost):
    text = "\n\n".join(blocks)
    body = {"text": text, "model_id": model,
            "voice_settings": {"stability": stability, "similarity_boost": similarity, "style": style, "use_speaker_boost": boost}}
    return ENDPOINT.format(voice_id=voice_id), body


def sentences_from_alignment(blocks, alignment):
    """Per-block start and end seconds from the character alignment of the joined text."""
    starts, ends = alignment["character_start_times_seconds"], alignment["character_end_times_seconds"]
    out, pos = [], 0
    for i, b in enumerate(blocks):
        a, z = pos, pos + len(b) - 1
        if z >= len(starts):
            raise ValueError("alignment is shorter than the text sent")
        out.append({"i": i, "text": b, "start": round(starts[a], 3), "end": round(ends[z], 3)})
        pos = z + 1 + 2          # the "\n\n" between blocks
    return out


def post(url, body, key):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"xi-api-key": key, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read())


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice-id", required=True)
    ap.add_argument("--model", default="eleven_multilingual_v2")
    ap.add_argument("--stability", type=float, default=0.40)
    ap.add_argument("--similarity", type=float, default=0.75)
    ap.add_argument("--style", type=float, default=0.20)
    ap.add_argument("--no-speaker-boost", action="store_true")
    ap.add_argument("--project", default=".")
    ap.add_argument("--narration", default="narration.txt")
    ap.add_argument("--out", default="narration")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    proj = Path(a.project)
    nar = proj / a.narration
    if not nar.exists():
        print(f"REFUSED: {nar} not found")
        return 2
    blocks = read_blocks(nar.read_text())
    if not blocks:
        print("REFUSED: narration.txt has no text")
        return 2
    url, body = build_request(blocks, a.voice_id, a.model, a.stability, a.similarity, a.style, not a.no_speaker_boost)
    chars = len(body["text"])
    brief = (proj / "BRIEF.md").read_text() if (proj / "BRIEF.md").exists() else ""
    ok = approved(brief)
    if a.dry_run:
        print("DRY RUN: no network call, nothing spent.")
        print(f"POST {url}")
        print(f"header xi-api-key: <{KEY_VAR} from the environment, not shown>   key present: {'yes' if os.environ.get(KEY_VAR) else 'NO'}")
        print(json.dumps(body, indent=2))
        print(f"{len(blocks)} sentence(s), {chars} characters; would write {a.out}.mp3 and {a.out}.sentences.json, and log {chars} characters to spend.log")
        print(f"spend gate: {'approved line found' if ok else 'NO approved ElevenLabs line under Spend approved in BRIEF.md; a live run would be refused'}")
        return 0
    if not ok:
        print('REFUSED: BRIEF.md has no approved line for ElevenLabs under "Spend approved". Write the cost estimate, get the go-ahead, then record it (references/spend-gate.md).')
        return 2
    key = os.environ.get(KEY_VAR)
    if not key:
        print(f"REFUSED: environment variable {KEY_VAR} is not set")
        return 2
    if chars > MAX_CHARS:
        print(f"REFUSED: {chars} characters is over the {MAX_CHARS} per request this script allows; split the narration")
        return 2
    try:
        res = post(url, body, key)
        mp3 = base64.b64decode(res["audio_base64"])
        sents = sentences_from_alignment(blocks, res["alignment"])
    except urllib.error.HTTPError as e:
        print(f"FAILED: HTTP {e.code} from ElevenLabs (nothing logged as spent)")
        return 1
    except (urllib.error.URLError, KeyError, ValueError) as e:
        print(f"FAILED: {type(e).__name__}: {e} (nothing logged as spent)")
        return 1
    (proj / f"{a.out}.mp3").write_bytes(mp3)
    (proj / f"{a.out}.sentences.json").write_text(json.dumps(
        {"characters": chars, "voice_id": a.voice_id, "model": a.model, "voice_settings": body["voice_settings"], "sentences": sents}, indent=2))
    with open(proj / "spend.log", "a") as f:
        f.write(f"{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')} elevenlabs characters={chars} voice={a.voice_id} model={a.model}\n")
    print(f"wrote {a.out}.mp3 and {a.out}.sentences.json: {len(sents)} sentence(s), {chars} characters logged to spend.log")
    return 0


if __name__ == "__main__":
    sys.exit(main())
