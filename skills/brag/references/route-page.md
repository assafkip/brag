# Route R1: an HTML page with render(t), captured frame by frame

Zero spend. This is the founder's method for the Sonos cut renderer (sonos-v3.html plus capture.py) and the right default when the product is a concept, because the UI is rebuilt from divs.

## How it works

- One page, 1920x1080. Each scene is an absolutely positioned layer. A function window.render(t) sets every layer's opacity, transform and text for time t. It is a pure function of t.
- No CSS transitions, no CSS animations, no setTimeout, no Math.random. The template page disables transitions and animations globally.
- scripts/render_frames.py opens the page in the installed Chrome (channel "chrome"), calls render(t) for each frame time and saves a PNG. Run with: uv run --with playwright python render_frames.py ...
- scripts/audio.py builds the soundtrack, scripts/mux.sh joins frames and sound.

## Steps

1. Copy templates/page.html (scaffold.sh already did: index.html). Build the scenes from STORYBOARD.md. Rebuild UI from divs and CSS using DESIGN.md values. Never paste a screenshot of a real app into a scene.
2. Motion rule: the founder rejected drift on still images. Every scene needs real movement: typed text, a stamp landing, a badge flipping, a cursor travelling, a card sliding in, a slow push on a rebuilt UI. One element moves at a time, so the eye knows where to look.
3. Render stills at 4 or 5 timestamps (one per scene, mid-scene) and look at every one:
   uv run --with playwright python <skill>/scripts/render_frames.py --page index.html --stills 2.5,7.5,13,18.5,25 --out boards
   Fix what you see before rendering the whole video.
4. Pin a UI to a moving screen (only if you have generated clips, route R2): track the screen with track.py or detect_screen.py, then pass --tracks name=path.json to render_frames.py; the page reads window.TRACKS[name][frameIndex] as four corners and applies a matching CSS matrix3d transform.
5. Render all frames: ... --total 28 --out frames. Build the soundtrack: python3 audio.py audio-plan.json. Mux: bash mux.sh frames soundtrack.wav renders/<name>.mp4 <poster-seconds>.
6. Verify: python3 verify.py renders/<name>.mp4 --project .

## Common failures

- Text with too little settled time: a label needs about 0.8 s fully visible, a headline about 0.3 s per word with a 1.2 s minimum.
- A concept label missing on a scene: keep the single #concept-label element above all scenes.
- Fonts not loaded at capture: the renderer waits for document.fonts.ready; use system fonts or local files. Prefer Menlo for monospace ids and hashes: the macOS default monospace draws a hyphen so long that "EV-0007" reads as an en dash.
- Shots counted wrongly: verify.py reads the SCENES table in index.html (the template defines it). Keep it exact, with the scenes tiling the video. The pixel detector cannot see soft dissolves between pale scenes (a product explainer cut: scene scores at most 0.07 against a 0.2 threshold); its own count is printed as information. Do not add hard cuts, tinted backgrounds or smaller cards to make it see transitions. That bends the design to fit a weak instrument.
- Cards touching the top labels at the end of a push: keep every card at least 100 px below the top edge at the largest scale.
- Moving a cursor: use the cursor(t, waypoints) helper in the template; compute each scene's cursor from its own waypoints and hide it outside its scene.
- A sentence that overstates the rule: when a scene states a rule in the product's voice, state all its conditions or none of them, and tag it with the requirement it comes from.
