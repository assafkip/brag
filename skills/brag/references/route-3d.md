# Route R4: a three.js page for a reference with real depth and a moving camera

Use this when STUDY.md shows the reference has a perspective camera, layers at different depths, or objects that morph from one idea into the next. A flat card page (route R1) cannot match that production (rulings.md, ruling 18). Zero spend.

## The shape (the same page contract as route R1)

- One page, 1920x1080, `window.render(t)` a pure function of t. No Math.random (use a hash of the index), no real time, no CSS transitions or animations, no setTimeout.
- three.js vendored locally, never loaded from a network: `bash <skill>/scripts/vendor_three.sh <project-dir>` writes `vendor/three.classic.js` from the npm package, pinned to 0.170.0 (published 2024-10-31). Any other pin must be at least two weeks old. Needs node and npm.
- Chrome through Playwright on the GPU. WebGL ran in headless installed Chrome on a Mac with no software-rendering flags; if frames come out black, try `--chrome-arg=--enable-gpu` and `--chrome-arg=--ignore-gpu-blocklist` on render_pipe.py.
- Start from `templates/page3d.html`. It renders one frame without any other file but the vendored library.

## Techniques the page template shows (each one comes from a reference study, so cite your own in STUDY.md)

- Flat vector surfaces (MeshBasicMaterial, no lighting) placed at 3D positions. Depth comes from position and value, not from shading.
- A perspective camera that always moves: a slow drift for the floor of motion and a pull-back or push-in that decelerates into the hold, so the energy has a slow floor and bursts above it.
- Fog or a depth gradient, so far layers fade toward the background colour. No blur.
- Parallax: layers at several depths, each moving at its own rate against the camera.
- Dots and rows of small shapes drifting across the frame edges at different speeds. They are never still.
- Morph from one idea into the next instead of a cut: one object survives the change of beat and changes position, size and colour across it.
- Arrivals ease out with overshoot and settle, as measured in the reference (STUDY.md section B2).
- A caption that writes in letter by letter, from DOM text set by render(t).

## Steps

1. STUDY.md filled and DIRECTIONS.md picked (SKILL.md steps 4 and 5). craft.json lists the techniques with a fingerprint each, so verify.py can find them in the page.
2. `bash <skill>/scripts/vendor_three.sh .` then copy `templates/page3d.html` to `index.html`. Keep the SCENES table exact (verify.py reads it).
3. Prove one beat by hand: render stills at three or four times in that beat and look at every one.
   `uv run --with playwright python <skill>/scripts/render_frames.py --page index.html --stills 1.5,3,4.5 --out boards`
4. Compare with the reference before the other beats: `uv run --with numpy --with pillow python <skill>/scripts/compare.py <reference.mp4> <your clip> --range 0:7`.
5. Show the stills and wait. Then render with `render_pipe.py` (frames go straight into ffmpeg; it stops under a free-space floor), build the soundtrack, mux, verify.

## Limits

- WebGL text is poor; keep type in the DOM and let render(t) set it.
- The look of a path-traced or After Effects reference is not reproduced by flat materials; say which parts of the reference you are not matching.
- Video textures and large images slow the render a lot; draw panel faces to a 2D canvas and upload it as a texture, redrawn only when it changes.
