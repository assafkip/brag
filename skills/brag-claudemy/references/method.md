# Method, and how Claudemy was actually made

A product video is a sequence of gates, each with a file and a check. The history below is the evidence for every gate.

## The shape

1. Brief with rulings (BRIEF.md, rulings.md). Founder rulings override everything.
2. Reference measured (reference.json from scripts/pace.py). Done means comes from the reference.
3. Design (DESIGN.md): from the real product's captured tokens, or a proposal the founder picks.
4. Storyboard and script (STORYBOARD.md, SCRIPT.md). Every on-screen line has a [src: ...] tag.
5. Route chosen and stated: R1 page, R2 generated shots, R3 Hyperframes beats.
6. Build, render stills first, look at them, then the full render.
7. Soundtrack (audio.py), mux (mux.sh).
8. Verify (verify.py). Report what was and was not verified.

## Worked example: Claudemy app tour (route R3, 2026-10-15)

- Captured the live app, wrote DESIGN.md from the captured tokens, approved a six-beat storyboard, wrote a BUILD-BRIEF with a timing contract, built one Hyperframes composition per beat with sub-agents, linted and snapshotted each, rendered.
- The website-to-video verifier then failed three checks on the first tour: no captured brand assets used, two headlines under the 80 px floor, two beats under 70 percent timeline coverage. Lessons: use the product's real visuals, keep headline type at or above 80 px, keep something moving for most of every beat.
- Brief: about 40 s, 6 beats, no narration, about 8 s of the real lesson audio when the player appears, soft felt-piano bed ducked under it.

## Worked example: Claudemy Sonos cut (routes R1 and R2, 2026-10-23)

- Option 1 chosen by the founder: full Sonos feel with generated studio images, run as its own project. Reference measured: about 4.1 s shots, 21 cuts in 90 s, moving on about 66 percent of frames.
- Render 1 (25.5 s): six generated stills (gpt-image-2, 1536x1024, high) with slow drift, real UI composited onto the screens, piano bed, real lesson voice. Measured: shots changing at 4.5, 8.5, 12.5, 16.5, 21.0 s, mean change 3.64, frames moving 71 percent, longest still 2.6 s.
  Founder ruling: "It's okay." Images need much more movement; drift is not enough. The voice cut out after "it starts with a line..." and the drop was too sharp. Motion should come from the founder's own tools that animate images.
- Render 2 (26.0 s): Kling 2.6 motion clips (test against Hailuo H3 first, founder picked Kling). Phone screen tracked with optical flow and a homography; laptop screen found per frame by dark-region detection. Mean change 4.18.
  Founder ruling: "This is close." The phone jitters; smooth it. The voice still stops at "I can't sha...": add the lines after it, and cut speech from transcript timestamps, never from loudness.
- Render 3 (28.1 s): phone track smoothed with a cubic path per corner (acceleration 0.758 px to 0.0018 px); voice ends on the full sentence; the last chord lands on its last word.
- Spend recorded: two test clips (about $3.50 to $3.80 each), six 5-second Kling clips (about $19 to $21 at $0.63 to $0.70 per second).
- The pace instrument cited in the notes (ref/motion.py) was lost. scripts/pace.py was rebuilt and calibrated to reproduce the recorded results of renders 1 and 2.

## What the history says to do

- Measure the reference before building, and re-measure every round.
- Put rulings into files at once; the voice cut was asked for twice before it stuck.
- Choose cuts from the transcript.
- Test motion tools on one clip before buying six.
- Pin UI to screens with tracking, then smooth the track.
