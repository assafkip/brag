"""Track a flat surface through a generated clip so a UI can be pinned to it.

  uv run --with opencv-python-headless --with numpy python track.py <clip.mp4> <out.json> <band> x1,y1 x2,y2 x3,y3 x4,y4

Corners are frame-0 pixels (TL, TR, BR, BL). Features are taken in a band of <band> px around the
quad (rim, bezel, the table the phone lies on), followed with pyramidal Lucas-Kanade, and each frame
gets a RANSAC homography from frame 0. Writes the 4 corners for every frame plus the inlier count, so a
frame where the fit is weak can be seen instead of silently trusted.
"""
import json
import sys

import cv2
import numpy as np

clip, out, band = sys.argv[1], sys.argv[2], int(sys.argv[3])
quad = np.array([[float(v) for v in p.split(",")] for p in sys.argv[4:8]], dtype=np.float32)
# "similarity" (scale, rotation, shift) suits a straight push-in at a face-on screen, where the
# keyboard below sits on another plane and drags a full homography off true (laptop clip, 2026-10-23)
model = sys.argv[8] if len(sys.argv) > 8 else "homography"

cap = cv2.VideoCapture(clip)
frames = []
while True:
    ok, f = cap.read()
    if not ok:
        break
    frames.append(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY))
h, w = frames[0].shape

outer = np.zeros((h, w), np.uint8)
cv2.fillConvexPoly(outer, quad.astype(np.int32), 255)
outer = cv2.dilate(outer, np.ones((band * 2 + 1, band * 2 + 1), np.uint8))
inner = np.zeros((h, w), np.uint8)
cv2.fillConvexPoly(inner, quad.astype(np.int32), 255)
inner = cv2.erode(inner, np.ones((15, 15), np.uint8))
mask = cv2.subtract(outer, inner)  # a ring around the surface; the blank screen itself has no features
if model == "similarity":
    mask[int(quad[:, 1].max()) - 10 :, :] = 0  # lid edges only: drop the hinge and keyboard

p0 = cv2.goodFeaturesToTrack(frames[0], maxCorners=600, qualityLevel=0.005, minDistance=6, mask=mask)
lk = dict(winSize=(31, 31), maxLevel=4, criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 40, 0.01))
pts, ref, alive = p0.copy(), p0.copy(), np.ones(len(p0), bool)
result = [{"corners": quad.tolist(), "inliers": int(len(p0))}]
for i in range(1, len(frames)):
    nxt, st, _ = cv2.calcOpticalFlowPyrLK(frames[i - 1], frames[i], pts, None, **lk)
    back, st2, _ = cv2.calcOpticalFlowPyrLK(frames[i], frames[i - 1], nxt, None, **lk)
    fb = np.linalg.norm((back - pts).reshape(-1, 2), axis=1)
    alive &= (st.ravel() == 1) & (st2.ravel() == 1) & (fb < 1.0)  # forward-backward check drops drifting points
    pts = nxt
    if model == "similarity":
        A, inl = cv2.estimateAffinePartial2D(ref[alive], pts[alive], method=cv2.RANSAC, ransacReprojThreshold=2.0)
        H = np.vstack([A, [0, 0, 1]])
    else:
        H, inl = cv2.findHomography(ref[alive], pts[alive], cv2.RANSAC, 2.0)
    c = cv2.perspectiveTransform(quad.reshape(-1, 1, 2), H).reshape(-1, 2)
    result.append({"corners": c.tolist(), "inliers": int(inl.sum()) if inl is not None else 0})
json.dump({"fps": cap.get(cv2.CAP_PROP_FPS), "frames": result}, open(out, "w"))
inl = [r["inliers"] for r in result]
print(f"{clip}: {len(frames)} frames, start features {len(p0)}, inliers min {min(inl)} median {int(np.median(inl))}")
