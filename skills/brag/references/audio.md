# Audio

## The soundtrack plan (scripts/audio.py)

A JSON plan (templates/audio-plan.json) drives a calm piano bed that changes chord with the shots, near-silent foley under on-screen actions, an optional real voice clip with the music ducked under it, fades, and a peak limit. Only numpy and ffmpeg. Chords available: F, Dm, Bb, C, Am, Gm, Em; add more in the plan under "chords" and "roots".

- bed: one entry per chord change, with optional "bass" and "arp". Bass enters on the reveal. A slow arpeggio plays once the product is on screen. To give each scene its own chord, set one bed entry per scene at the scene's start time from the SCENES table (for example scenes at 0, 4.5, 9, 14, 19, 23.5 give six entries), and set "total" to the video's length.
- foley: soft ticks, a stamp, a click. Barely there. No sound on text reveals.
- ring: a final note timed to the last word of the voice, or the end card.
- voice: file, start, length, at. Use real audio only.

## Voice rules (founder, 2026-10-23)

- Cut speech at transcript word timestamps (whisper word times), never at a loudness dip. A loudness-picked end fell inside the word "shake".
- End a clip on a natural pause, after the full sentence. Never a hard stop mid-sentence.
- Duck the music about 0.2 s before the voice and bring it back about 0.7 s after, so the hand-off has no dip. The last chord lands on the end of the last word.

## Narration (only when the brief asks for it)

`python3 <skill>/scripts/voice.py --voice-id <id> --dry-run` shows the request. A live run needs an approved ElevenLabs line under "Spend approved" in BRIEF.md and the key in the environment variable ELEVENLABS_API_KEY (never in a file, never on a command line). One sentence per blank-line block in narration.txt. It writes narration.mp3, narration.sentences.json (start and end seconds per sentence) and logs the characters to spend.log. Cut and duck by the sentence times, as in the voice rules above. Voice choice and settings are judged by ear; see the worked example in method.md. Adding a library voice to the account can need a permission the key does not have, even when listing voices works.

## Loudness and format

- mux.sh normalises to -16 LUFS with true peak at most -1.5 dBTP, AAC 192k at 48 kHz.
- verify.py accepts integrated loudness within 1.5 LU of -16 and true peak at most -1.0 dBTP.

## Music from other sources

If a bundled or downloaded cue is used, record its license and write the credit line into SCRIPT.md under Share copy. Cues that need attribution (for example CC BY 4.0) must carry it.
