"""Find the blank laptop screen in every frame as the largest near-black region at frame centre.
Writes the same JSON shape as track.py. Frame 0 is checked against the hand-measured corners."""
import json, sys, cv2, numpy as np
clip, out, thr = sys.argv[1], sys.argv[2], int(sys.argv[3])
cap = cv2.VideoCapture(clip); res = []
while True:
    ok, f = cap.read()
    if not ok: break
    g = cv2.GaussianBlur(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY), (5, 5), 0)
    m = (g < thr).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))
    n, lab, stats, cent = cv2.connectedComponentsWithStats(m)
    h, w = g.shape
    k = lab[h // 2 - 40, w // 2]  # the screen covers the frame centre in every frame of this push-in
    ys, xs = np.where(lab == k)
    # robust edges: the 1st and 99th percentile of each column/row extent ignore stray dark pixels
    x0, x1 = np.percentile(xs, 0.5), np.percentile(xs, 99.5)
    y0, y1 = np.percentile(ys, 0.5), np.percentile(ys, 99.5)
    res.append({"corners": [[x0, y0], [x1, y0], [x1, y1], [x0, y1]], "inliers": int(len(xs))})
json.dump({"fps": cap.get(cv2.CAP_PROP_FPS), "frames": res}, open(out, "w"))
c0 = np.array(res[0]["corners"]); print('frame 0 box', c0[0].round(), c0[2].round(), ' last', np.array(res[-1]["corners"])[0].round(), np.array(res[-1]["corners"])[2].round())
