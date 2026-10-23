# Founder rulings for product videos

These carry into every project (scaffold.sh copies this file). They override anything in a brief. When the founder gives a new ruling during a build, append it here, with the date and his words, in the same turn, before acting on it. Machine-checkable parts also go into rulings.json.

Sources: the owner's notes from the two Claudemy video projects (2026-10-15 and 2026-10-23) and his working rules on iteration.

1. No emdashes and no double hyphens in visible text. Enforced by scripts/copylint.py.
2. Nothing confidential appears: no client names, no material marked confidential (on the Claudemy tour, one confidential course was kept out of every frame). Project-specific words go in rulings.json "forbidden_words".
3. Match the reference's pace, not only its colors. Measure the reference and every render with the same instrument (scripts/pace.py) and compare to the reference, not to the previous attempt. The Sonos reference: about 4.1 s shots, frames moving about 66 percent, small chapter labels, minimal type, photographic objects.
4. Ken Burns drift on stills is not enough. Motion comes from real movement: generated video clips, or UI that animates. (Founder, after render 1: "the images need much more movement".)
5. When a different look is asked for, do not use the product site's look. The look follows the reference.
6. Voices in the video are the product's own real output. Never invent testimonials or dialogue. No narration unless the brief asks for it.
7. Cut speech at transcript word timestamps, never at a loudness dip. End a clip on a natural pause. The music hands off to the voice and back with no dip. (Founder, after renders 2 and 3: the voice stopped mid-word at "shake" because the cut was chosen from loudness.)
8. Smooth tracked screens. Report the frame-to-frame acceleration before and after smoothing. (Render 3: 0.758 px to 0.0018 px, residual mean 0.45 px.)
9. Spend gate: state the cost, test one clip in two ways, let the founder pick, log the spend. Nothing that costs money runs without an approved line in BRIEF.md "Spend approved". See spend-gate.md.
10. Done means is measured. Define it before building, check it after every round, report each result as a number. "It looks right" is not done.
11. Every ruling goes into a file the code reads, in the same turn. Never only into a brief or a prompt. Each brief carries all prior rulings, not just the latest.
12. The same failure twice means stop that worker and diagnose the root cause with a fresh one. At most three rounds on one class of fix, then report what was tried, what failed and the state. Do not start round four.
13. Prove the shape by hand before building machinery.
14. One worker per job. Two workers on overlapping files cost more than they save.
15. Render settings: 1920x1080, 30 fps, h264 crf 17, yuv420p, AAC 192k at 48 kHz, loudness normalised to -16 LUFS with true peak at most -1.5 dBTP, the poster frame baked into frame 0 from a hero frame.
16. Built product: real copy only. Every on-screen claim traces to the product's README, spec or demo, and carries a [src: ...] tag in SCRIPT.md. Concept product: all data on screen is invented, the label "Concept preview" is on every scene, and no prices, customers or numbers about speed or accuracy appear.
17. Report what was not verified. Any failed or skipped check goes into the final summary verbatim.
