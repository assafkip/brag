# STUDY: what the reference does, measured

Reference: {{path or link, size, frame rate, length}}
Frames looked at: {{contact sheets, with the time ranges they cover}}
Numbers (scripts/pace.py, the same instrument that will measure our video): {{whole reference: mean change, frames moving percent, longest still. Then the matching range only, if we copy one section}}

Write what you SEE, with a time, before you decide what to copy. Where a line is a guess about how it was made, start it with INFERENCE. Do not write anything from memory of the video or from a summary of it: if a file you meant to read is missing, say so here.

## A. Techniques seen (each cites a time; at least 12)

1. {{0.0 to 1.5 s: what appears, where from, how many, at what sizes}}
2. {{time: what builds in, in what order (does content grow in, or pop?)}}
3. {{time: how depth is shown (value, blur, scale, parallax)}}
4. {{time: camera move and its easing}}
5. {{time: background treatment}}
6. {{time: particles, dots, rows: speed, direction, are they ever still}}
7. {{time: the one accent moment}}
8. {{time: the shot change: what carries it (a shape, an object that survives, a wipe)}}
9. {{time: type: how often, how big, how it arrives}}
10. {{time: overshoot and settle: which objects}}
11. {{time: energy: the slow floor and where the bursts are}}
12. {{time: anything else that would be missed if you copied only the layout}}

## B. Forensics: measure first, then label the inference

### B1. Frame rate and hold
Container rate, then count exactly repeated consecutive frames (change under 0.05 grey levels). Movement on ones (a new drawing every frame) or on twos, and for which range.

### B2. Easing, from tracking one object
Track one object over a move (centroid per 2 frames). List its positions and per-frame velocity. Say what the curve is: linear, ease-in, ease-out, overshoot and settle, anticipation before the move.

### B3. Background treatment
Flat, gradient, grid, texture. Is there grain or banding. Does it move.

### B4. Number of things on screen
Per beat: how many objects at once, how many sizes, how many at the same time are moving.

### B5. What survives each shot change
Per cut: the object, colour or shape that is the same before and after (or "nothing: a hard cut").

### B6. Drawing type per beat (2D flat vector, true 3D, faked depth, particles and dots, kinetic type)

- Beat 1 ({{start}} to {{end}} s): {{type}}. Evidence: {{what you saw, time}}
- Beat 2 ({{start}} to {{end}} s): {{type}}. Evidence: {{what you saw, time}}

### B7. INFERENCE (labelled)
How it was probably made, and what that means for how we make ours. None of it is proven if the source files are not visible.

## C. What our video copies, and what it does not

Every line names a technique number from section A, so craft.json can cite it.

- Copies: {{technique number: how we will make it}}
- Does not copy: {{technique number: why}}
