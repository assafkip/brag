# Reader brief

What you hand an independent reader (ruling 37), and the row the reader's session writes back.

A reader is a fresh session that has not seen the brief, the storyboard or the script. It sees the
finished video, or the contact sheet plus the narration, and nothing about what the video was trying
to do.

## Why the narration goes with the frames

Five readers of the openwitness cut were shown contact sheets only, with the sound left out. All five
retold the story correctly and all five still said LEAVE, mostly "leans on the narration" or "product
arrives late". The narration carried the beat they said was missing. The retell was a useful
instrument; the verdict reached without the audio was not (ASK-3036).

So a reader gets the audio, or the transcript with timestamps. A verdict on silent frames measures
the capture, not the cut.

## What the reader is given

1. The finished video, or the contact sheet from `scripts/compare.py`.
2. The narration transcript, one line per narration block, each line opening with its timestamp:

   ```
   [00:00] Fraud leads do not get a second look at a case.
   [00:06] Openwitness holds the whole trail in one place.
   [00:13] Every claim carries where it came from.
   ```

   The timestamps come from the cut, not from the script: read them off the render, or off the
   per-block durations `scripts/voice.py` wrote next to the narration audio.
3. Nothing else. No brief, no storyboard, no claim list.

## What the reader is asked

1. **Retell.** In your own words, what happened, in order? One line per beat.
2. **Verdict.** With the sound on, would the intended viewer stay to the end, or leave? `STAY` or
   `LEAVE`, and one line of why.
3. **Coverage.** Of the numbered narration lines above, which did your retell actually cover?

## The row the session appends to `readers.jsonl`

```json
{"reader": "sonnet-transcript-1", "verdict": "STAY", "why": "the trail is clear by the second beat",
 "retell_matched": 7, "retell_total": 8, "video_sha256": "<sha256 of the exact file watched>"}
```

| Field | What it holds |
|---|---|
| `reader` | the session's id, unique per reader |
| `verdict` | `STAY` or `LEAVE`. Any LEAVE fails the check |
| `why` | one line |
| `retell_matched` | how many of the narration lines the retell covered |
| `retell_total` | how many narration lines the reader was given |
| `video_sha256` | the sha256 of the exact render; rows for an older render do not count |

`scripts/chain_checks.py` `readers_check` reads the pair: it reports the coverage next to the
verdict, warns when a judging row records none (that verdict was reached without the narration), and
fails a pair that cannot be a count of lines matched out of the total.

Coverage is reported, not gated. A low retell on a cut everyone stays for is a finding about the
narration, and which way to fix it is the founder's call, not the check's.
