from pathlib import Path
from PIL import Image
import cv2
import torch
import math 
import function.utils_rotate as utils_rotate
from IPython.display import display
import os
import time
import argparse
import function.helper as helper

ROOT = Path(__file__).resolve().parent
YOLOV5_DIR = ROOT / 'yolov5'
MODEL_DIR = ROOT / 'model'

# load model
yolo_LP_detect = torch.hub.load(str(YOLOV5_DIR), 'custom', path=str(MODEL_DIR / 'LP_detector_nano_61.pt'), force_reload=True, source='local')
yolo_license_plate = torch.hub.load(str(YOLOV5_DIR), 'custom', path=str(MODEL_DIR / 'LP_ocr_nano_62.pt'), force_reload=True, source='local')
yolo_license_plate.conf = 0.60

prev_frame_time = 0
new_frame_time = 0

ap = argparse.ArgumentParser()
ap.add_argument('--camera', type=int, default=0, help='camera index (default 0)')
args = ap.parse_args()

vid = cv2.VideoCapture(args.camera)
if not vid.isOpened():
    raise RuntimeError(f'Unable to open camera index {args.camera}. Try a different index, such as 0 or 1.')

# vid = cv2.VideoCapture("1.mp4")
while True:
    ret, frame = vid.read()
    if not ret or frame is None:
        raise RuntimeError('Failed to read frame from camera. Check that the selected camera index is correct and the camera is connected.')
    
    plates = yolo_LP_detect(frame, size=640)
    list_plates = plates.pandas().xyxy[0].values.tolist()
    list_read_plates = set()
    for plate in list_plates:
        flag = 0
        x = int(plate[0]) # xmin
        y = int(plate[1]) # ymin
        w = int(plate[2] - plate[0]) # xmax - xmin
        h = int(plate[3] - plate[1]) # ymax - ymin  
        crop_img = frame[y:y+h, x:x+w]
        cv2.rectangle(frame, (int(plate[0]),int(plate[1])), (int(plate[2]),int(plate[3])), color = (0,0,225), thickness = 2)
        cv2.imwrite("crop.jpg", crop_img)
        rc_image = cv2.imread("crop.jpg")
        lp = ""
        for cc in range(0,2):
            for ct in range(0,2):
                lp = helper.read_plate(yolo_license_plate, utils_rotate.deskew(crop_img, cc, ct))
                if lp != "unknown":
                    list_read_plates.add(lp)
                    cv2.putText(frame, lp, (int(plate[0]), int(plate[1]-10)), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (36,255,12), 2)
                    flag = 1
                    break
            if flag == 1:
                break
            
    new_frame_time = time.time()
    fps = 1/(new_frame_time-prev_frame_time)
    prev_frame_time = new_frame_time
    fps = int(fps)
    cv2.putText(frame, str(fps), (7, 70), cv2.FONT_HERSHEY_SIMPLEX, 3, (100, 255, 0), 3, cv2.LINE_AA)
    cv2.imshow('frame', frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

vid.release()
cv2.destroyAllWindows()