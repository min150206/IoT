from pathlib import Path
from PIL import Image
import cv2
import torch
import time
import argparse
import requests
import threading

import function.utils_rotate as utils_rotate
import function.helper as helper
from dashboard import db as database

# ==================== CONFIG ====================
ROOT = Path(__file__).resolve().parent
YOLOV5_DIR = ROOT / 'yolov5'
MODEL_DIR = ROOT / 'model'

ESP32_IP = "192.168.137.50"   # change to your ESP32 IP
ESP32_PORT = 80
ESP32_URL = f"http://{ESP32_IP}:{ESP32_PORT}"

DETECT_COOLDOWN = 5          # seconds, avoid re-processing the same plate right after it's confirmed
STABLE_CONFIRM_TIME = 3      # seconds the SAME plate text must be read continuously before it's accepted



# ==================== LOAD MODELS ====================
print("Loading YOLO models...")
yolo_LP_detect = torch.hub.load(str(YOLOV5_DIR), 'custom',
                                 path=str(MODEL_DIR / 'LP_detector_nano_61.pt'),
                                 force_reload=True, source='local')
yolo_license_plate = torch.hub.load(str(YOLOV5_DIR), 'custom',
                                     path=str(MODEL_DIR / 'LP_ocr_nano_62.pt'),
                                     force_reload=True, source='local')
yolo_license_plate.conf = 0.60
print("Models loaded.")

database.init_db()


# ==================== ESP32 COMMANDS ====================

def send_command(endpoint: str):
    """Send an HTTP GET command to the ESP32. Non-blocking via thread."""
    def _send():
        try:
            requests.get(f"{ESP32_URL}/{endpoint}", timeout=3)
        except requests.exceptions.RequestException as e:
            print(f"[ESP32] Failed to send '{endpoint}': {e}")
    threading.Thread(target=_send, daemon=True).start()


def signal_checking():
    """Blue blinking LED - verifying plate (not yet stable)."""
    send_command("checking")


def signal_open():
    """Solid green LED - plate confirmed, gate open."""
    send_command("open")


def signal_closed():
    """Red LED - gate closed (idle state). Only used at startup here."""
    send_command("closed")


# ==================== PLATE PROCESSING ====================

def process_plate(plate_text: str):
    """
    Decide checkin or checkout based on current DB state,
    then trigger the gate.
    """
    plate_text = plate_text.upper().strip()

    if database.is_in_lot(plate_text):
        database.checkout(plate_text)
        print(f"[CHECKOUT] {plate_text}")
    else:
        database.checkin(plate_text)
        print(f"[CHECKIN] {plate_text}")

    signal_open()


# ==================== MAIN LOOP ====================

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--camera', type=int, default=0, help='camera index (default 0)')
    args = ap.parse_args()

    vid = cv2.VideoCapture(args.camera)
    if not vid.isOpened():
        raise RuntimeError(f'Unable to open camera index {args.camera}.')

    prev_frame_time = 0
    last_plate_time = {}        # plate -> last confirmed/processed timestamp (cooldown)

    # Tracks the last signal sent, just to avoid spamming "checking" repeatedly. The ESP32 owns the actual open -> closed transition.
    current_signal = "closed"   # one of: "closed", "checking", "open"

    # Stability tracking: same plate text must persist for STABLE_CONFIRM_TIME seconds
    candidate_plate = None
    candidate_since = None

    signal_closed()  # initial state: gate closed, red LED
    current_signal = "closed"

    while True:
        ret, frame = vid.read()
        if not ret or frame is None:
            print("Failed to read frame from camera.")
            break

        plates = yolo_LP_detect(frame, size=640)
        list_plates = plates.pandas().xyxy[0].values.tolist()

        plate_seen_this_frame = len(list_plates) > 0
        now = time.time()

        if plate_seen_this_frame:
            # Only send "checking" while we haven't confirmed a plate yet.
            # Once open, stay open (don't blink) even if still reading the same plate.
            if current_signal != "open" and current_signal != "checking":
                signal_checking()
                current_signal = "checking"

        read_this_frame = None  # the plate text successfully read in this frame, if any

        for plate in list_plates:
            x = int(plate[0])
            y = int(plate[1])
            w = int(plate[2] - plate[0])
            h = int(plate[3] - plate[1])
            crop_img = frame[y:y+h, x:x+w]

            cv2.rectangle(frame, (x, y), (int(plate[2]), int(plate[3])),
                          color=(0, 0, 225), thickness=2)

            lp = "unknown"
            flag = 0
            for cc in range(0, 2):
                for ct in range(0, 2):
                    lp = helper.read_plate(yolo_license_plate, utils_rotate.deskew(crop_img, cc, ct))
                    if lp != "unknown":
                        flag = 1
                        break
                if flag == 1:
                    break

            if lp != "unknown":
                read_this_frame = lp
                cv2.putText(frame, lp, (x, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (36, 255, 12), 2)

        # ---------- Stability check (3s of the same plate before accepting) ----------

        if read_this_frame is not None:
            if read_this_frame == candidate_plate:
                stable_duration = now - candidate_since
                cv2.putText(frame, f"Stabilizing: {stable_duration:.1f}s",
                            (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 255), 2)

                if stable_duration >= STABLE_CONFIRM_TIME and current_signal != "open":
                    last_time = last_plate_time.get(read_this_frame, 0)
                    if now - last_time > DETECT_COOLDOWN:
                        last_plate_time[read_this_frame] = now
                        process_plate(read_this_frame)
                        current_signal = "open"
                    # reset candidate so it must re-stabilize before triggering again
                    candidate_plate = None
                    candidate_since = None
            else:
                # different plate text read, restart stability timer
                candidate_plate = read_this_frame
                candidate_since = now
        else:
            # nothing read this frame, drop the candidate
            candidate_plate = None
            candidate_since = None

        # FPS counter
        new_frame_time = time.time()
        fps = 1 / (new_frame_time - prev_frame_time) if prev_frame_time else 0
        prev_frame_time = new_frame_time
        cv2.putText(frame, str(int(fps)), (7, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 3, (100, 255, 0), 3, cv2.LINE_AA)
        cv2.putText(frame, f"Signal: {current_signal}", (10, 140),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

        cv2.imshow('frame', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    vid.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
