from flask import Flask, render_template, request, jsonify
import requests
import db as database

#Local host website: http://localhost:5000

app = Flask(__name__)

ESP32_IP = "192.168.137.50"   # change to your ESP32 IP
ESP32_URL = f"http://{ESP32_IP}"


@app.route("/")
def index():
    return render_template("index.html")


# ==================== API: VEHICLES ====================

@app.route("/api/current")
def api_current():
    rows = database.get_current_vehicles()
    data = [{"plate": p, "checkin": ci.strftime("%Y-%m-%d %H:%M:%S")} for p, ci in rows]
    return jsonify(data)


@app.route("/api/search")
def api_search():
    plate = request.args.get("plate", "")
    rows = database.search_vehicle(plate)
    data = [{
        "plate": p,
        "checkin": ci.strftime("%Y-%m-%d %H:%M:%S"),
        "checkout": co.strftime("%Y-%m-%d %H:%M:%S") if co else None
    } for p, ci, co in rows]
    return jsonify(data)


@app.route("/api/vehicle/add", methods=["POST"])
def api_add_vehicle():
    plate = request.json.get("plate", "")
    if not plate:
        return jsonify({"ok": False, "error": "Plate is required"}), 400
    ok = database.checkin(plate)
    if ok:
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "Vehicle already in the lot"}), 409


@app.route("/api/vehicle/remove", methods=["POST"])
def api_remove_vehicle():
    plate = request.json.get("plate", "")
    if not plate:
        return jsonify({"ok": False, "error": "Plate is required"}), 400
    ok = database.checkout(plate)
    if ok:
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "Vehicle not in the lot"}), 409


# ==================== API: LOGS ====================

@app.route("/api/logs")
def api_logs():
    plate = request.args.get("plate") or None
    limit = int(request.args.get("limit", 50))
    rows = database.get_logs(plate, limit)
    data = [{
        "plate": p,
        "action": action,
        "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S")
    } for p, action, ts in rows]
    return jsonify(data)


# ==================== API: ESP32 STATUS ====================

@app.route("/api/gate-status")
def api_gate_status():
    try:
        r = requests.get(f"{ESP32_URL}/status", timeout=2)
        if r.status_code == 200:
            return jsonify({"online": True, **r.json()})
    except requests.exceptions.RequestException:
        pass
    return jsonify({"online": False, "state": "unknown", "presence": False})


if __name__ == "__main__":
    database.init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
