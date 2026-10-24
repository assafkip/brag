---
name: brag
description: Make a short product video, about 25 to 30 seconds, from a brief, a spec or a real product, using the founder's own method from the Claudemy videos. It writes the brief and rulings first, measures a reference video for pace, designs and storyboards every scene with a source tag on every line, builds a rendered-frame page (or generated shots, or Hyperframes beats), makes a calm soundtrack, renders, and then runs a verifier that checks loudness, pace, copy rules, sources and the poster frame. It never spends money without an approved line and never shows a concept as if it were working software. Use when someone asks for a measured, source-tagged or concept-labelled product video, says "the Claudemy method", "brag", or "build a video from this spec", or wants pace measured against a reference. For a quick one-command launch video of a built project, the original brag-upstream skill is the lighter choice.
license: MIT
---

# brag (the founder's product video method)

This is the Claudemy method, bundled. The two Claudemy videos are the worked examples (references/method.md): the app tour built from Hyperframes beats on 2026-10-15, and the Sonos cut built from generated shots, real UI and measured pace on 2026-10-23. The method is a sequence of gates, each with a file and a check. The checks are scripts, so they do not depend on you remembering them.

Scripts live in this skill's `scripts/` folder (the base directory shown when the skill loads). Call them by absolute path. Read `references/rulings.md` first: the founder's rulings override anything else.

## Inputs
- A brief in words, a spec file, or a live product URL. Ask only for what is missing.
- Whether the product is built (STATUS: BUILT) or a concept (STATUS: CONCEPT). If unsure, it is CONCEPT. Read `references/claims.md`.

## Before starting
Check and say in one line what is missing: `ffmpeg`, `ffprobe`, `python3` with `numpy`, `uv`, Google Chrome installed. Rendering needs `uv run --with playwright`; tracking needs `uv run --with opencv-python-headless --with numpy`.

## Workflow

1. **Scaffold.** `bash <skill>/scripts/scaffold.sh <project-dir> "<Name>" concept|built`. It creates BRIEF.md, rulings.md, rulings.json, DESIGN.md, STORYBOARD.md, SCRIPT.md, reference.json, audio-plan.json and index.html. Work inside the project folder from now on. Never run this skill inside a folder that holds client data, credentials or a private repo: build in a clean folder and copy in only what the video needs.

2. **Brief.** Fill BRIEF.md with the user. Add forbidden words (client names, confidential material) to rulings.json. If the user gives a ruling at any point, append it to rulings.md (and rulings.json if a script can check it) in that same turn, before acting on it.

3. **Reference.** Ask for a reference video. Put every reference's name in reference.json under "references" (verify.py checks STUDY.md names each). If a local clip exists, run `python3 <skill>/scripts/pace.py <reference.mp4> --json` and write the targets into reference.json. If not, keep the template (Sonos, measured 2026-10-23), write in BRIEF.md that the numbers come from the owner's notes and were not re-measured, and say so in the report. The done-means is these numbers, set before building.

4. **Reference forensics (required before design).** Fill STUDY.md (templates/STUDY.md, scaffolded): at least 12 techniques each with a time, frame rate and hold, easing measured by tracking one object, background, number of things on screen, what survives each shot change, and the drawing type per beat (2D flat vector, true 3D, faked depth, particles, kinetic type). Match the reference's production and not only its grammar (rulings 18, 27, 28). verify.py prints WARN, not FAIL, if STUDY.md is missing or has fewer than 12 cited techniques. Then list the techniques you will take in craft.json (templates/craft.json), each citing a time from STUDY.md with a fingerprint found in index.html.

4b. **Design.** Fill the Vision section of BRIEF.md with the person's own words, write three directions in DIRECTIONS.md and get a pick (ruling 33). Then DESIGN.md. BUILT: from the real product's captured design. CONCEPT: a proposal; the founder picks. Say what the look is not.

5. **Storyboard and script.** STORYBOARD.md (about 5 scenes of 4 to 6 seconds, a small chapter label each, one idea per scene) and SCRIPT.md. Every line under "## On-screen text" ends with `[src: id]`. If a line has no source, it does not go on screen. Show both files to the user and get the go-ahead before building.

6. **Choose the route and say it.** Name the options and mark the pick:
   - R1 page (default, no spend): `references/route-page.md`.
   - R2 generated shots with motion, real UI composited: `references/route-generated.md`. Costs money; needs the spend gate.
   - R3 Hyperframes beats: `references/route-beats.md`.
   - R4 three.js page, for a reference with a moving perspective camera or layered depth, no spend: `references/route-3d.md`, `templates/page3d.html`, `scripts/vendor_three.sh`.
   Read `references/spend-gate.md` before anything that costs money. No approved line in BRIEF.md "Spend approved", no spend.

7. **Build.** Follow the route file. Prove one beat by hand, render stills first and look at every one, show them and wait (rulings 19, 20). Fix what you see before the full render. Render with `scripts/render_pipe.py` when disk is tight or the page is heavy (rulings 24). If the brief asks for narration, `scripts/voice.py` (spend gate applies). Then `python3 <skill>/scripts/audio.py audio-plan.json` and `bash <skill>/scripts/mux.sh frames soundtrack.wav renders/<name>.mp4 <poster-seconds>`.

8. **Verify.** `python3 <skill>/scripts/verify.py renders/<name>.mp4 --project .`. Fix every FAIL. The pace gate reads a per-tile max change (`area_moving_pct`, `longest_area_still_s`) against the same reference.json keys, because a whole-frame mean cannot see a small element moving on a flat page and failed an approved UI-on-white cut; the whole-frame mean follows as a "whole-frame" INFO row and gates nothing (ASK-3036). The readers gate reads each row's `retell_matched` out of `retell_total` next to the verdict, and WARNs on a judging row that records none, because a STAY or LEAVE reached on silent frames measures the capture and not the cut; what the reader is handed is `references/reader-brief.md` (ASK-3036). Re-measure after each round and compare to the reference, not to the last attempt. verify.py counts shots from the SCENES table in index.html, because the pixel detector cannot see soft dissolves between similar scenes; it prints the detector's own count as information. Never change the design (cuts, backgrounds, card sizes) to make a detector see a transition: if a check cannot measure something your design does on purpose, report the limit. At most three rounds on one class of fix; if the same failure happens twice, stop and diagnose before a third try. Compare with the reference each round: `uv run --with numpy --with pillow python <skill>/scripts/compare.py <reference.mp4> <video>`. verify.py writes a receipt; show the video only after `verify.py <video> --check-receipt` exits 0 (ruling 36), and remember a clean run is necessary and not proof (ruling 25). Then report.

9. **Share copy.** Write it in SCRIPT.md under "Share copy". Short, plain, no claim without a source tag. Add any music credit line.

## Done means
- verify.py prints no FAIL, and its "not verified" list is reported to the user as it is.
- The founder has seen the video, not only the numbers.
- Spend, if any, is logged in plan.md against the approved line.

## Final report (short)
Files and paths, the verify.py output verbatim, what was not verified, spend, rulings added this session, and the one next step.

## Lessons from the design chain
Rulings 27 to 38 bring in what transfers from the design-chain method: quote or time-stamp the reference, ground the build in the study, a craft manifest checked against the page, distance to the reference measured with a control, three directions, vision in the person's words, critique dispositions, a receipt before showing, independent readers, and warn-before-fail for new checks. Sources and what was not taken: `references/method.md`.

## Hard rules
- No emdashes, no double hyphens in visible text; `scripts/copylint.py` runs inside verify.py.
- No narration unless the brief asks for it, then only through `scripts/voice.py` behind the spend gate. No invented quotes or testimonials; a voice that speaks for the product is its own real output.
- Concept mode: label on every scene, invented data only, no prices, customers, or numbers about speed or accuracy.
- Never print, copy or commit a key.
- Nothing is published or posted by this skill.
