import psycopg2
from datetime import datetime

# ==================== CONFIG ====================
DB_CONFIG = {
    "host":     "localhost",
    "port":     5432,
    "dbname":   "IoT",
    "user":     "postgres",
    "password": "Mh121531"  # change to your password
}


def get_conn():
    return psycopg2.connect(**DB_CONFIG)


# ==================== INIT ====================

def init_db():
    """Create tables if they do not exist."""
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS vehicles (
            id       SERIAL PRIMARY KEY,
            plate    TEXT NOT NULL,
            checkin  TIMESTAMP NOT NULL,
            checkout TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id        SERIAL PRIMARY KEY,
            plate     TEXT NOT NULL,
            action    TEXT NOT NULL CHECK(action IN ('checkin', 'checkout')),
            timestamp TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)

    conn.commit()
    c.close()
    conn.close()
    print("Database initialized.")


# ==================== HELPERS ====================

def is_in_lot(plate: str) -> bool:
    """Check if a vehicle is currently in the lot (checked in but not checked out)."""
    plate = plate.upper().strip()
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT 1 FROM vehicles
        WHERE plate = %s AND checkout IS NULL
    """, (plate,))
    found = c.fetchone() is not None
    c.close(); conn.close()
    return found


# ==================== CHECK IN / OUT ====================

def checkin(plate: str) -> bool:
    """
    Check in a vehicle.
    Returns False if the vehicle is already in the lot.
    """
    plate = plate.upper().strip()
    if is_in_lot(plate):
        return False

    now = datetime.now()
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO vehicles (plate, checkin) VALUES (%s, %s)", (plate, now))
    c.execute("INSERT INTO logs (plate, action, timestamp) VALUES (%s, 'checkin', %s)", (plate, now))
    conn.commit()
    c.close(); conn.close()
    return True


def checkout(plate: str) -> bool:
    """
    Check out a vehicle by updating the checkout time.
    Returns False if the vehicle is not in the lot.
    """
    plate = plate.upper().strip()
    if not is_in_lot(plate):
        return False

    now = datetime.now()
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        UPDATE vehicles SET checkout = %s
        WHERE plate = %s AND checkout IS NULL
    """, (now, plate))
    c.execute("INSERT INTO logs (plate, action, timestamp) VALUES (%s, 'checkout', %s)", (plate, now))
    conn.commit()
    c.close(); conn.close()
    return True


# ==================== VEHICLES ====================

def get_all_vehicles() -> list:
    """Return all records (both in lot and already left)."""
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT plate, checkin, checkout FROM vehicles ORDER BY checkin DESC")
    rows = c.fetchall()
    c.close(); conn.close()
    return rows


def get_current_vehicles() -> list:
    """Return only vehicles currently in the lot."""
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT plate, checkin FROM vehicles
        WHERE checkout IS NULL
        ORDER BY checkin DESC
    """)
    rows = c.fetchall()
    c.close(); conn.close()
    return rows


def search_vehicle(plate: str) -> list:
    """Search vehicles by partial plate match."""
    plate = plate.upper().strip()
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT plate, checkin, checkout FROM vehicles
        WHERE plate LIKE %s
        ORDER BY checkin DESC
    """, (f"%{plate}%",))
    rows = c.fetchall()
    c.close(); conn.close()
    return rows


def remove_vehicle(plate: str) -> bool:
    """Delete all records of a plate. Returns False if not found."""
    plate = plate.upper().strip()
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM vehicles WHERE plate = %s", (plate,))
    affected = c.rowcount
    conn.commit()
    c.close(); conn.close()
    return affected > 0


# ==================== LOGS ====================

def get_logs(plate: str = None, limit: int = 50) -> list:
    """Get log history. Filter by plate if provided."""
    conn = get_conn()
    c = conn.cursor()
    if plate:
        plate = plate.upper().strip()
        c.execute("""
            SELECT plate, action, timestamp FROM logs
            WHERE plate LIKE %s
            ORDER BY timestamp DESC LIMIT %s
        """, (f"%{plate}%", limit))
    else:
        c.execute("""
            SELECT plate, action, timestamp FROM logs
            ORDER BY timestamp DESC LIMIT %s
        """, (limit,))
    rows = c.fetchall()
    c.close(); conn.close()
    return rows


#===================== RESET ===================

def reset_db():
    """Delete all records from both tables."""
    conn = get_conn()
    c = conn.cursor()
    c.execute("TRUNCATE TABLE vehicles, logs RESTART IDENTITY")
    conn.commit()
    c.close(); conn.close()
    print("Database reset.")


# ==================== MAIN ====================

if __name__ == "__main__":
    init_db()
    print("=== Parking Database CLI ===")
    print("Commands: checkin / checkout / list / current / search / remove / logs / reset / quit\n")

    while True:
        cmd = input(">>> ").strip().lower()

        if cmd == "quit":
            print("Bye!")
            break

        elif cmd == "checkin":
            plate = input("Plate: ").strip()
            if checkin(plate):
                print(f"{plate.upper()} checked in.")
            else:
                print(f"{plate.upper()} is already in the lot.")

        elif cmd == "checkout":
            plate = input("Plate: ").strip()
            if checkout(plate):
                print(f"{plate.upper()} checked out.")
            else:
                print(f"{plate.upper()} is not in the lot.")

        elif cmd == "list":
            rows = get_all_vehicles()
            if rows:
                print(f"\n{'Plate':<15} {'Check-in':<22} {'Check-out'}")
                print("-" * 60)
                for plate, ci, co in rows:
                    co_str = co.strftime("%Y-%m-%d %H:%M:%S") if co else "Still in lot"
                    print(f"{plate:<15} {ci.strftime('%Y-%m-%d %H:%M:%S'):<22} {co_str}")
                print()
            else:
                print("No records found.")

        elif cmd == "current":
            rows = get_current_vehicles()
            if rows:
                print(f"\n{'Plate':<15} {'Check-in'}")
                print("-" * 40)
                for plate, ci in rows:
                    print(f"{plate:<15} {ci.strftime('%Y-%m-%d %H:%M:%S')}")
                print()
            else:
                print("Parking lot is empty.")

        elif cmd == "search":
            plate = input("Search plate: ").strip()
            rows = search_vehicle(plate)
            if rows:
                print(f"\n{'Plate':<15} {'Check-in':<22} {'Check-out'}")
                print("-" * 60)
                for plate, ci, co in rows:
                    co_str = co.strftime("%Y-%m-%d %H:%M:%S") if co else "Still in lot"
                    print(f"{plate:<15} {ci.strftime('%Y-%m-%d %H:%M:%S'):<22} {co_str}")
                print()
            else:
                print("No results found.")

        elif cmd == "remove":
            plate = input("Plate: ").strip()
            if remove_vehicle(plate):
                print(f"All records of {plate.upper()} removed.")
            else:
                print(f"{plate.upper()} not found.")

        elif cmd == "logs":
            plate = input("Filter by plate (Enter to show all): ").strip()
            rows = get_logs(plate if plate else None)
            if rows:
                print(f"\n{'Plate':<15} {'Action':<10} {'Timestamp'}")
                print("-" * 45)
                for plate, action, ts in rows:
                    print(f"{plate:<15} {action:<10} {ts.strftime('%Y-%m-%d %H:%M:%S')}")
                print()
            else:
                print("No logs found.")
        elif cmd == "reset":
            confirm = input("Reset all data? (yes/no): ").strip().lower()
            if confirm == "yes":
                reset_db()
            else:
                print("Reset cancelled.")

        else:
            print("Unknown command. Try: checkin / checkout / list / current / search / remove / logs / reset /quit")