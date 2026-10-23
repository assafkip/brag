import json, sys, cv2, numpy as np
clip, track, out = sys.argv[1:4]
T = json.load(open(track))["frames"]
cap = cv2.VideoCapture(clip); tiles=[]; i=0
want = {0, len(T)//2, len(T)-1}
while True:
    ok, f = cap.read()
    if not ok: break
    if i in want:
        c = np.array(T[i]["corners"], np.int32)
        cv2.polylines(f, [c], True, (0, 0, 255), 3)
        tiles.append(cv2.resize(f, (640, 360)))
    i += 1
cv2.imwrite(out, np.hstack(tiles))
