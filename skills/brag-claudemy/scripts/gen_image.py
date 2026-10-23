"""Generate one landscape still with OpenAI image generation.

  python3 gen_image.py <out.png> "<prompt>" [model]

Reads the key from the file named by BRAG_OPENAI_KEY_FILE (default ~/.config/brag/openai-key); never prints it.
THIS SPENDS MONEY. Run it only after the spend gate in references/spend-gate.md has an approved line.
Gemini was tried first and returned 402 (prepaid credits depleted), 2026-10-23.
"""
import base64
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

out, prompt = sys.argv[1], sys.argv[2]
model = sys.argv[3] if len(sys.argv) > 3 else "gpt-image-2"
import os
key = Path(os.environ.get("BRAG_OPENAI_KEY_FILE", str(Path.home() / ".config/brag/openai-key"))).read_text().strip()
body = {"model": model, "prompt": prompt, "size": "1536x1024", "quality": "high", "n": 1}
req = urllib.request.Request(
    "https://api.openai.com/v1/images/generations",
    data=json.dumps(body).encode(),
    headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
)
t0 = time.time()
try:
    with urllib.request.urlopen(req, timeout=300) as r:
        d = json.load(r)
except urllib.error.HTTPError as e:
    sys.exit(f"{out}: HTTP {e.code} {json.loads(e.read() or b'{}').get('error', {}).get('message', '')[:200]}")
open(out, "wb").write(base64.b64decode(d["data"][0]["b64_json"]))
print(f"{out} {time.time() - t0:.0f}s usage={d.get('usage')}")
