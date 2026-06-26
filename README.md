# Vietnamese License Plate Recognition


This repository provides you with a detailed guide on how to training and build a Vietnamese License Plate detection and recognition system. This system can work on 2 types of license plate in Vietnam, 1 line plates and 2 lines plates.


- **Pretrained model** provided in ./model folder in this repo 

- **Download yolov5 (old version) from this link:** [yolov5 - google drive](https://drive.google.com/file/d/1g1u7M4NmWDsMGOppHocgBKjbwtDA-uIu/view?usp=sharing)

- Copy yolov5 folder to project folder

## Run License Plate Recognition

```bash
  # run inference on webcam (15-20fps if there is 1 license plate in scene)
  python webcam.py 


  # run inference on image
  python lp_image.py -i test_image/3.jpg
  # run LP_recognition.ipynb if you want to know how model work in each step
```

## Vietnamese Plate Dataset

This repo uses 2 sets of data for 2 stage of license plate recognition problem:

- [License Plate Detection Dataset](https://drive.google.com/file/d/1xchPXf7a1r466ngow_W_9bittRqQEf_T/view?usp=sharing)
- [Character Detection Dataset](https://drive.google.com/file/d/1bPux9J0e1mz-_Jssx4XX1-wPGamaS8mI/view?usp=sharing)


## Training

**Training code for Yolov5:**

Use code in ./training folder
```bash
  training/Plate_detection.ipynb     #for LP_Detection
  training/Letter_detection.ipynb    #for Letter_detection
```

---

## Automatic Parking System (this project)

This project builds on the recognition pipeline above to power an IoT automatic parking system. A webcam reads license plates, a PostgreSQL database tracks check-in/check-out, and an ESP32-S3 controls a gate indicator (RGB LED) over WiFi.

### How it works

```
Webcam -> YOLOv5 (plate detection) -> YOLOv5 (OCR) -> stable plate confirmed
   -> check database (checkin or checkout) -> send command to ESP32
   -> ESP32 updates RGB LED (blue / green / red)
   -> no plate detected for 3s -> auto-close (red)
```

- **Blue (blinking)** — a plate is detected, waiting for it to stabilize (3 seconds of the same reading)
- **Green (solid)** — plate confirmed, gate open
- **Red (solid)** — gate closed / idle

### Additional project structure

```
Proj/
├── main.py                          # Camera detection + gate control logic (include the human sensor logic)
├── README.md
├── main_no_hd.py                    # Camera detection + gate control logic (without the human sensor logic)
├── webcam.py                        #Camera and model test (used for testing)
├── tempCodeRunnerFile.py            #temp file
├── requirement.txt                  #Requirement file (libraries for python)
|
├── dashboard/
│   ├── app.py                       # Flask web dashboard
│   ├── db.py                        # Database functions (PostgreSQL)
│   ├── templates/
│   │   └── index.html
│   └── static/
│       ├── style.css
│       └── script.js
|
├── function/                         # Folder used for AI model
├── trainning/
├── yolov5/                           #YOLOv5 model
├── model/                            #Trained model
|
└── Boardcode/   # ESP32 code
```

### Hardware

- **ESP32-S3 Dev Kit (MKE-K01)** — runs the gate controller firmware, drives the onboard RGB LED
- **Webcam** (laptop camera) — used as the detection source

### Additional software requirements

```bash
pip install flask requests psycopg2-binary
```

Also requires a local **PostgreSQL** database (default name: `IoT`).

### Setup

1. **Database** — create a PostgreSQL database and update the credentials in `dashboard/db.py`:
   ```python
   DB_CONFIG = {
       "host": "localhost",
       "port": 5432,
       "dbname": "IoT",
       "user": "postgres",
       "password": "your_password"
   }
   ```

2. **ESP32 firmware** — open `gate_controller_no_sensor.ino` in Arduino IDE:
   - Set your WiFi SSID/password
   - Set a static IP matching your hotspot/router subnet
   - Flash to the ESP32-S3 (Board: ESP32S3 Dev Module, PSRAM: OPI PSRAM)
   - Check the Serial Monitor (115200 baud) to confirm the IP address

3. **Update ESP32 IP** in both:
   - `main.py` → `ESP32_IP`
   - `dashboard/app.py` → `ESP32_IP`

   (Both must match the static IP set in the firmware.)

### Running

Run the detection backend and the dashboard in separate terminals — they share the same database.

```bash
# Terminal 1 — camera detection + gate control
python main.py --camera 0

# Terminal 2 — web dashboard
cd dashboard
python app.py
```

Open the dashboard at: **http://localhost:5000**

### Dashboard features

- Live gate status (synced with the ESP32 RGB LED state)
- List of vehicles currently in the lot
- Search by plate (including past check-outs)
- Manual check-in / check-out
- Check-in / check-out history log

### ESP32 HTTP endpoints

| Endpoint | Method | Description |
|----------|--------|--------------|
| `/checking` | GET | Set state to checking (blue blink) |
| `/open` | GET | Set state to open (solid green) |
| `/closed` | GET | Set state to closed (solid red) |
| `/status` | GET | Returns current state as JSON |

### Notes

- A plate must be read consistently for 3 seconds before it is accepted (reduces false reads from OCR noise)
- The gate auto-closes 3 seconds after no plate is detected in frame
