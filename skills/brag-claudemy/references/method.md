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

## Worked example: a product explainer matched to a reference video (route R4, 2026-10-23)

- The first three builds matched the reference's beats, labels and palette and passed verify.py, and were rejected by eye each time. The measurement behind the rejection: 51 percent of frames moving against 83 percent for the reference. The reference moved a perspective camera through layered 3D panels; the builds put flat static cards on a page. Lesson: the grammar was copied and the production was not (rulings 18 and 25).
- The fix was a study before the design (templates/STUDY.md): every technique with a time, the frame rate and holds, easing from tracking one object, how each beat is drawn (flat vector, true 3D, faked depth, particles, kinetic type), and what survives each shot change. The study showed movement on ones, ease-out with overshoot, a drawn gradient trail and not shutter blur, and a real 3D camera in some beats. Then one beat was proved by hand with three.js (route-3d.md) before the others were built.
- A render filled the disk: hundreds of PNG frames. render_pipe.py streams frames into ffmpeg and stops under a free-space floor (ruling 24).
- Narration, as a worked example and not a rule: the first voices tried sounded like announcers and were rejected. The person chose a conversational American male voice, ElevenLabs stability 0.40, similarity 0.75, style 0.20, speaker boost on (the defaults in scripts/voice.py). Voice settings are judged by ear: render one sentence, listen, change one setting. Reading the voice list with an API key can work while adding a library voice to the account needs a permission the key may lack, so pick from the voices the key can already list, or have the person add the voice in their account.
- Sound: voice plus a quiet bed. The earlier cut with whooshes and clicks was not wanted (ruling 22).

## Lessons from the design chain (added 2026-10-23)

A design-round method in the kipi-system repository (plugins/kipi-core/commands/design-chain.md and q-system/.q-system/scripts/design-chain-gate.py) runs: vision, owners, brief with verbatim anchors, three directions, craft manifest, build, measure, critique, proof, checks, readers, seal. The parts that transfer to making a video from a reference video are rulings 27 to 38, each with its source and each held by a check in scripts/chain_checks.py, scripts/compare.py or scripts/verify.py:

- Vision first, in the person's own words (34): verify.py "vision".
- Study the reference with times (27, 28) and re-read the whole set when one is added (32): verify.py "study".
- Three directions before a build (33): verify.py "directions".
- A craft manifest whose techniques cite the study and are found in the page (29): verify.py "craft".
- Measure the distance to the reference with a control (30, 31): compare.py.
- Critique with dispositions (35): verify.py "critique".
- Receipt before showing (36): verify.py writes it, `--check-receipt` reads it.
- Independent readers (37): verify.py "readers".
- New checks warn before they fail (38).

Considered and not taken: "owners per decision". In the source an owner is a file the builder must have read in full this session, held by a hook that reads the session transcript; a video project has no such record to check, and its single sources (rulings.md for copy, reference.json for pace, STUDY.md for production) are already how this skill is laid out. The source's web-only measurements (CSS axes, anti-pattern browser detector) do not apply to video.

## What the history says to do

- Measure the reference before building, and re-measure every round.
- Put rulings into files at once; the voice cut was asked for twice before it stuck.
- Choose cuts from the transcript.
- Test motion tools on one clip before buying six.
- Pin UI to screens with tracking, then smooth the track.
