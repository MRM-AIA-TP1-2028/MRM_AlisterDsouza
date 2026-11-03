import cv2, numpy as np
from collections import deque
from typing import TypedDict

marker_in_cm=5.0

blue = (
    np.array([90, 60, 100]),
    np.array([110, 210, 255])
)

yellow = ( 
    np.array([25,80,80]), 
    np.array([45,255,255]) 
          )

min_area_px = 100
MAX_JUMP_PX = 100

kernel = np.ones((5,5),np.uint8)

aruco = cv2.aruco.ArucoDetector(cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50), cv2.aruco.DetectorParameters())

class State(TypedDict):
    scale: float | None
    selected: tuple[int, int] | None
    trail: deque[tuple[int, int]]
    blues: list[np.ndarray]

def get_mask(hsv,rng):

    m = cv2.inRange(hsv,*rng)
    m = cv2.morphologyEx(m,cv2.MORPH_OPEN,kernel)
    return cv2.morphologyEx(m,cv2.MORPH_CLOSE,kernel)

def contours(mask):

    cs, _ = cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    return [c for c in cs if cv2.contourArea(c) > min_area_px]

def center(c):

    m=cv2.moments(c)
    return int(m["m10"]/m["m00"]), int(m["m01"]/m["m00"])

def find_scale(frames):

    corners, ids, _ = aruco.detectMarkers(frames)
    if ids is None:
        return None

    cv2.aruco.drawDetectedMarkers(frames, corners, ids)
    pts = corners[0][0]
    side_px = np.mean([np.linalg.norm(pts[i] - pts[(i+1)%4]) for i in range(4)])
    return side_px / marker_in_cm

def find_ball(hsv):

    best=None

    for c in contours(get_mask(hsv,yellow)):
        area, per = cv2.contourArea(c), cv2.arcLength(c,True)

        if 4 * np.pi * area / per**2 > 0.7 and (best is None or area > best[0]):
            (x,y), r = cv2.minEnclosingCircle(c)
            best = (area, (int(x),int(y)), int(r))
    return best[1:] if best else None

def process(frame, state: State):

    hsv = cv2.cvtColor(cv2.GaussianBlur(frame, (7, 7), 0), cv2.COLOR_BGR2HSV)
    scale = find_scale(frame) or state["scale"]
    state["scale"] = scale
    cm2 = lambda px2: f"{px2 / scale**2:.1f} cm2" if scale else "no marker"

    if scale:
        cv2.putText(
        frame,
        f"Scale: {scale:.2f} px/cm",
        (20, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 0),
        2
    )
    else:
        cv2.putText(
        frame,
        "ArUco marker not detected",
        (20, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 0, 255),
        2
    )

    ball = find_ball(hsv)
    bx = by = 0
    if ball:
        (bx, by), r = ball
        cv2.circle(frame, (bx, by), int(r), (0, 255, 255), 2)
        cv2.circle(frame, (bx, by), 3, (0, 0, 255), -1)
        cv2.putText(frame, f"Ball c=({bx},{by}) r={r:.0f}px A={cm2(np.pi * r**2)}",
                    (bx - 60, by - int(r) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
 

    blues = state["blues"] = contours(get_mask(hsv, blue))
    cv2.imshow("Blue Detection Mask", get_mask(hsv, blue))
    sel, tracked = state["selected"], None
    if sel is not None and blues:
                             
        near = min(blues, key=lambda c: np.hypot(*np.subtract(center(c), sel)))
        if np.hypot(*np.subtract(center(near), sel)) < MAX_JUMP_PX:
            tracked = near
            state["selected"] = center(tracked)
            state["trail"].append(state["selected"])

    for c in blues:

        is_sel = sel is None or c is tracked
        x, y, w, h = cv2.boundingRect(c)
        cx, cy = center(c)
        color = (255, 0, 0) if is_sel else (120, 60, 60)
        cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
        cv2.circle(frame, (cx, cy), 4, (0, 0, 255), -1)
        cv2.putText(frame, f"Blue A={cm2(cv2.contourArea(c))}", (x, max(y - 8, 15)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        if is_sel and ball:

            cv2.line(frame, (cx, cy), (bx, by), (0, 255, 0), 1)
            k, unit = (scale, "cm") if scale else (1, "px")
            dx, dy = (cx - bx) / k, (by - cy) / k
            rel = f"{abs(dx):.1f}{unit} {'right' if dx > 0 else 'left'}, {abs(dy):.1f}{unit} {'above' if dy > 0 else 'below'} the ball"
            cv2.putText(frame, rel, (x, min(y + h + 18, frame.shape[0] - 6)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 150, 0), 2)
    if len(state["trail"]) > 1:

        cv2.polylines(frame, [np.array(state["trail"], np.int32).reshape(-1, 1, 2)], False, (0, 165, 255), 2)
    return frame
 
def main():
    
    state: State = State(
        scale=None,
        selected=None,
        trail=deque(maxlen=64),
        blues=[],
    )
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise SystemExit("Could not open camera (try VideoCapture(1))")
 
    def on_click(event, x, y, *_):

        if event == cv2.EVENT_LBUTTONDOWN:

            for c in (state.get("blues") or []):

                if cv2.pointPolygonTest(c, (x, y), False) >= 0:

                    state["selected"] = center(c); state["trail"].clear()
    cv2.namedWindow("tracker"); cv2.setMouseCallback("tracker", on_click)
 
    while True:

        ok, frame = cap.read()
        if not ok: break
        cv2.imshow("tracker", process(frame, state))
        k = cv2.waitKey(1) & 0xFF
        if k == ord("c"): state["selected"] = None; state["trail"].clear()
        if k == ord("q") or cv2.getWindowProperty("tracker", cv2.WND_PROP_VISIBLE) < 1: break
    cap.release(); cv2.destroyAllWindows()
 
if __name__ == "__main__":
    main()