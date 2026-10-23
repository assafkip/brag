#!/usr/bin/env python3
"""Soundtrack from a plan: a calm piano bed that changes with the shots, near-silent foley under on-screen
actions, and an optional real voice clip with the music ducked under it. Only numpy and ffmpeg are needed.

  python3 audio.py plan.json        writes plan["out"] (48 kHz stereo wav)

Plan (see templates/audio-plan.json):
  total, sr, seed, out, peak
  bed    [{at, chord, bass?, arp?}]  one chord per entry, held until the next entry; names from chords/roots
  chords {name: [midi...]}, roots {name: midi}   optional extra or overriding chords
  ring   {at, midi}                  one last note, e.g. on the final word of the voice
  foley  [{at, n, gap, cut, gain, dur}]  n soft ticks, gap seconds apart, low-passed at cut Hz
  voice  {file, start, length, at, gain, fade_in, fade_out}   real audio only, cut at the given start and length
  duck   {depth, pre, post, release}  music dips by depth while the voice plays, back after post seconds
  fade_in, fade_out

Founder rules built in (claudemy sonos cut, 2026-10-23):
  * speech start and length come from transcript word timestamps, never from a loudness dip (a loudness-picked
    end fell inside the word "shake");
  * the music starts rising before the voice ends and is back after it, so the hand-off has no dip;
  * the last chord lands on the end of the last word, so the silence after it is never heard as a drop.

Adapted from the owner's Claudemy Sonos-cut soundtrack script.
"""
import json
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

CH = {"F": [53, 57, 60, 64], "Dm": [50, 53, 57, 60], "Bb": [46, 50, 53, 57], "C": [48, 52, 55, 62], "Am": [45, 52, 55, 60],
      "Gm": [43, 46, 50, 55], "Em": [52, 55, 59, 62]}
ROOT = {"F": 41, "Dm": 38, "Bb": 34, "C": 36, "Am": 33, "Gm": 31, "Em": 40}


def build(plan, base_dir="."):
    SR = int(plan.get("sr", 48000))
    TOTAL = float(plan["total"])
    N = int(TOTAL * SR)
    rng = np.random.default_rng(int(plan.get("seed", 11)))
    chords = {**CH, **{k: v for k, v in plan.get("chords", {}).items()}}
    roots = {**ROOT, **{k: v for k, v in plan.get("roots", {}).items()}}
    music, fx = np.zeros((2, N)), np.zeros((2, N))

    def hz(m):
        return 440.0 * 2 ** ((m - 69) / 12)

    def tt(d):
        return np.arange(int(d * SR)) / SR

    def add(buf, start, sig, gain=1.0, pan=0.0):
        i = int(start * SR)
        if i >= N or i < 0:
            return
        sig = sig[: N - i] * gain
        buf[0, i:i + len(sig)] += sig * np.sqrt(0.5 * (1 - pan))
        buf[1, i:i + len(sig)] += sig * np.sqrt(0.5 * (1 + pan))

    def lp(sig, cutoff):
        a = np.exp(-2 * np.pi * cutoff / SR)
        out, y = np.empty_like(sig), 0.0
        for i, x in enumerate(sig):
            y = (1 - a) * x + a * y
            out[i] = y
        return out

    def piano(m, d=3.5, soft=0.55):
        t = tt(d)
        f = hz(m)
        s = sum((1 / k ** 1.7) * np.sin(2 * np.pi * f * k * t * (1 + 0.0004 * k)) * np.exp(-t * (0.9 + 0.8 * k)) for k in range(1, 6))
        return s * np.clip(t / 0.008, 0, 1) * soft

    def pad(ms, d):
        t = tt(d)
        s = sum(np.sin(2 * np.pi * hz(m) * t * (1 + 0.001 * np.sin(2 * np.pi * 0.25 * t))) for m in ms)
        return s / len(ms) * np.clip(t / 1.0, 0, 1) * np.clip((d - t) / 1.0, 0, 1)

    def bass(m, d):
        t = tt(d)
        return (np.sin(2 * np.pi * hz(m) * t) + 0.25 * np.sin(4 * np.pi * hz(m) * t)) * np.exp(-t * 1.4) * np.clip(t / 0.02, 0, 1)

    def tick(d=0.03, cut=2200):
        t = tt(d)
        return lp(rng.standard_normal(len(t)), cut) * np.exp(-t * 150)

    bed = plan["bed"]
    for i, e in enumerate(bed):
        s = float(e["at"])
        nxt = float(bed[i + 1]["at"]) if i + 1 < len(bed) else TOTAL
        c = chords[e["chord"]]
        for j, m in enumerate(c):
            add(music, s + 0.015 * j, piano(m, d=min(4.5, TOTAL - s)), 0.2, pan=-0.3 + 0.2 * j)
        add(music, s, pad([m + 12 for m in c], nxt - s + 0.8), 0.045)
        if e.get("bass"):
            add(music, s, bass(roots[e["chord"]], nxt - s), 0.28)
        if e.get("arp"):
            step = (nxt - s) / 6
            for k, m in enumerate([c[1] + 12, c[2] + 12, c[3] + 12, c[2] + 12, c[3] + 12, c[1] + 24]):
                add(music, s + k * step, piano(m, d=1.6, soft=0.45), 0.06, pan=0.35 if k % 2 else -0.35)
    if plan.get("ring"):
        r = plan["ring"]
        add(music, float(r["at"]), piano(int(r["midi"]), d=max(0.5, TOTAL - float(r["at"])), soft=0.5), 0.08)

    for f in plan.get("foley", []):
        for k in range(int(f.get("n", 1))):
            jitter = rng.uniform(-0.01, 0.01) if f.get("n", 1) > 1 else 0.0
            add(fx, float(f["at"]) + k * float(f.get("gap", 0.1)) + jitter, tick(f.get("dur", 0.03), f.get("cut", 2200)),
                f.get("gain", 0.05) * (rng.uniform(0.85, 1.15) if f.get("n", 1) > 1 else 1.0), pan=rng.uniform(-0.15, 0.15))

    t_all = np.arange(N) / SR
    vb = np.zeros((2, N))
    duck = np.ones(N)
    v = plan.get("voice")
    if v:
        src = Path(base_dir) / v["file"]
        clip = Path(base_dir) / (Path(plan["out"]).stem + "-voice.wav")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(v["start"]), "-t", str(v["length"]), "-i", str(src),
                        "-vn", "-ac", "1", "-ar", str(SR), str(clip)], check=True)
        with wave.open(str(clip)) as w:
            voice = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(float) / 32768
        fi, fo = int(v.get("fade_in", 0.04) * SR), int(v.get("fade_out", 0.12) * SR)
        voice[:fi] *= np.linspace(0, 1, fi)
        voice[-fo:] *= np.linspace(1, 0, fo)
        voice = voice / (np.max(np.abs(voice)) + 1e-9) * float(v.get("gain", 0.8))
        add(vb, float(v["at"]), voice)
        dk = plan.get("duck", {})
        d0, d1 = float(v["at"]) - float(dk.get("pre", 0.2)), float(v["at"]) + float(v["length"])
        duck = 1 - float(dk.get("depth", 0.6)) * np.clip((t_all - d0) / 0.2, 0, 1) * np.clip((d1 + float(dk.get("post", 0.7)) - t_all) / float(dk.get("release", 1.2)), 0, 1)

    mix = music * duck + np.vstack([lp(fx[0], 6000), lp(fx[1], 6000)]) + vb
    mix *= np.clip(t_all / float(plan.get("fade_in", 0.4)), 0, 1) * np.clip((TOTAL - t_all) / float(plan.get("fade_out", 1.2)), 0, 1)
    mix /= np.max(np.abs(mix)) / float(plan.get("peak", 0.89))
    out = Path(base_dir) / plan["out"]
    with wave.open(str(out), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(mix.T, -1, 1) * 32767).astype(np.int16).tobytes())
    return out, TOTAL


if __name__ == "__main__":
    plan_path = Path(sys.argv[1]).resolve()
    out, total = build(json.loads(plan_path.read_text()), str(plan_path.parent))
    print(f"{out} {total}s")
