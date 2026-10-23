# Route R2: generated studio shots with motion, real UI composited on screens

This costs money. Do not start it without an approved spend line (spend-gate.md). It is the route the founder used for the Sonos cut, and the look he said was "close".

## Steps (as done on 2026-10-23)

1. Stills: gpt-image-2, 1536x1024, quality high, one scene per image, photographic studio objects, soft light, no text in the image. scripts/gen_image.py <out.png> "<prompt>". Screens in the image stay blank or near-black so real UI can be composited onto them. Gemini image returned 402 (prepaid credits depleted) on 2026-10-23.
2. Motion test first: make the same shot with two tools (Kling 2.6 via the Apify actor pnda/kling-video-generator, and Hailuo H3) and look at both side by side. Kling showed a red band on a headband from 3.0 s; Hailuo had no artifacts but a harder push at 720p. The founder picked. Sora 2 API was shut down (model shutdown_date 2026-09-24, /v1/videos returned 404).
3. Clips: 16:9 crop of the still (1536x864 at y=80, scaled to 1920x1080), 5 s, 1080p, 24 fps. Check every clip for artifacts. For a shot that must hold longer than 5 s, slow it: ffmpeg setpts=1.47*PTS with minterpolate (mi_mode=mci) to keep the motion smooth.
4. Track screens so the UI stays pinned:
   - flat surface with visible rim or table around it: scripts/track.py <clip> <out.json> <band> x1,y1 x2,y2 x3,y3 x4,y4 (corners TL, TR, BR, BL on frame 0). Pyramidal Lucas-Kanade features in a band around the surface, a RANSAC homography per frame. It writes inlier counts so a weak frame is visible.
   - face-on screen in a straight push-in, where the keyboard sits on another plane: pass "similarity" as the last argument, so scale, rotation and shift are fitted and the keyboard cannot drag the fit.
   - blank dark screen: scripts/detect_screen.py <clip> <out.json> <threshold> finds the near-black region per frame (threshold 10 on the laptop clip).
   - look at the result: scripts/draw_track.py <clip> <track.json> <out.jpg> draws the tracked corners on three frames.
   Run these with: uv run --with opencv-python-headless --with numpy python <script> ...
5. Smooth the tracks: cubic path per corner. Report frame-to-frame acceleration before and after, and remove any one-frame spike.
6. Build the page (route R1) with each clip as a frame sequence (clip frames extracted with ffmpeg) and the real UI pinned to the tracked corners.
7. Audio: bed, foley and any real voice clip; cut speech at transcript word timestamps (references/audio.md).

## Rules

- Real UI is composited, never generated. Screen text is never part of the generated image.
- Test one clip before buying six.
- Log every generation in plan.md with the cost.
