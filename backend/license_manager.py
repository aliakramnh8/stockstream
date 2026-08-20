import sqlite3
import os
import uuid
import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

ADMIN_PASSWORD_HASH = hashlib.sha256("alinh7".encode()).hexdigest()

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "licenses.db"))

def get_db():
    if DATABASE_URL:
        import psycopg2
        url = DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        conn = psycopg2.connect(url)
        return conn, "postgres"
    else:
        conn = sqlite3.connect(DB_PATH)
        return conn, "sqlite"

def init_db():
    try:
        conn, db_type = get_db()
        cursor = conn.cursor()
        if db_type == "postgres":
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS licenses (
                    id SERIAL PRIMARY KEY,
                    license_key VARCHAR(100) UNIQUE NOT NULL,
                    client_name VARCHAR(255) DEFAULT '',
                    duration_days INTEGER DEFAULT 30,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    status VARCHAR(50) DEFAULT 'active',
                    device_id VARCHAR(255) DEFAULT ''
                )
            """)
            cursor.execute("DELETE FROM licenses WHERE license_key = %s", ("SS-MASTER-2026",))
        else:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS licenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    license_key TEXT UNIQUE NOT NULL,
                    client_name TEXT DEFAULT '',
                    duration_days INTEGER DEFAULT 30,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    status TEXT DEFAULT 'active',
                    device_id TEXT DEFAULT ''
                )
            """)
            cursor.execute("DELETE FROM licenses WHERE license_key = ?", ("SS-MASTER-2026",))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error initializing DB: {e}")

def generate_key(prefix="SS") -> str:
    part1 = uuid.uuid4().hex[:4].upper()
    part2 = uuid.uuid4().hex[:4].upper()
    part3 = uuid.uuid4().hex[:4].upper()
    return f"{prefix}-{part1}-{part2}-{part3}"

class LicenseManager:
    def __init__(self):
        init_db()

    def check_admin_password(self, password: str) -> bool:
        return hashlib.sha256(password.encode()).hexdigest() == ADMIN_PASSWORD_HASH

    def create_license(self, client_name: str = "Client", days: int = 30) -> Dict[str, Any]:
        key = generate_key()
        now = datetime.now()
        expires_at = now + timedelta(days=days)
        exp_str = expires_at.strftime("%Y-%m-%d %H:%M:%S")

        conn, db_type = get_db()
        cursor = conn.cursor()
        if db_type == "postgres":
            cursor.execute("""
                INSERT INTO licenses (license_key, client_name, duration_days, expires_at, status)
                VALUES (%s, %s, %s, %s, 'active')
            """, (key, client_name, days, expires_at))
        else:
            cursor.execute("""
                INSERT INTO licenses (license_key, client_name, duration_days, expires_at, status)
                VALUES (?, ?, ?, ?, 'active')
            """, (key, client_name, days, exp_str))
        conn.commit()
        conn.close()

        return {
            "success": True,
            "license_key": key,
            "client_name": client_name,
            "duration_days": days,
            "expires_at": exp_str,
            "status": "active"
        }

    def verify_license(self, key: str, device_id: str = "") -> Dict[str, Any]:
        clean_key = key.strip().upper()
        if not clean_key:
            return {"valid": False, "message": "Please enter a license key."}

        conn, db_type = get_db()
        cursor = conn.cursor()
        if db_type == "postgres":
            cursor.execute("""
                SELECT license_key, client_name, duration_days, expires_at, status, device_id
                FROM licenses WHERE license_key = %s
            """, (clean_key,))
        else:
            cursor.execute("""
                SELECT license_key, client_name, duration_days, expires_at, status, device_id
                FROM licenses WHERE license_key = ?
            """, (clean_key,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            return {"valid": False, "message": "Invalid License Key. Please enter a valid purchased key."}

        license_key, client_name, duration_days, expires_at_raw, status, saved_device_id = row

        if status != 'active':
            conn.close()
            return {"valid": False, "message": "This license key has been revoked/deactivated."}

        # 1-Device Lock: Bind key to the first device that activates it
        if device_id:
            if not saved_device_id:
                if db_type == "postgres":
                    cursor.execute("UPDATE licenses SET device_id = %s WHERE license_key = %s", (device_id, clean_key))
                else:
                    cursor.execute("UPDATE licenses SET device_id = ? WHERE license_key = ?", (device_id, clean_key))
                conn.commit()
            elif saved_device_id != device_id:
                conn.close()
                return {
                    "valid": False,
                    "message": "This license key is already activated on another computer (Single Device Limit). Sharing is not allowed."
                }
        conn.close()

        try:
            if isinstance(expires_at_raw, datetime):
                expires_at = expires_at_raw
                expires_at_str = expires_at.strftime("%Y-%m-%d %H:%M:%S")
            else:
                expires_at_str = str(expires_at_raw)
                expires_at = datetime.strptime(expires_at_str.split(".")[0], "%Y-%m-%d %H:%M:%S")

            now = datetime.now()
            if now > expires_at:
                return {"valid": False, "message": f"License expired on {expires_at_str}. Please renew."}

            delta = expires_at - now
            days_remaining = max(0, delta.days)
            display_days = days_remaining if days_remaining > 0 else (1 if delta.total_seconds() > 0 else 0)

            return {
                "valid": True,
                "client_name": client_name,
                "expires_at": expires_at_str,
                "days_remaining": display_days,
                "license_key": license_key
            }
        except Exception as e:
            return {"valid": False, "message": f"Error validating license: {e}"}

    def list_all_licenses(self) -> List[Dict[str, Any]]:
        conn, db_type = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, license_key, client_name, duration_days, created_at, expires_at, status
            FROM licenses ORDER BY id DESC
        """)
        rows = cursor.fetchall()
        conn.close()

        result = []
        now = datetime.now()
        for r in rows:
            id_, key, name, days, created, expires, status = r
            try:
                if isinstance(expires, datetime):
                    exp_dt = expires
                    exp_str = exp_dt.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    exp_str = str(expires)
                    exp_dt = datetime.strptime(exp_str.split(".")[0], "%Y-%m-%d %H:%M:%S")
                is_expired = now > exp_dt
            except:
                exp_str = str(expires)
                is_expired = False

            display_status = "expired" if is_expired and status == "active" else status
            result.append({
                "id": id_,
                "license_key": key,
                "client_name": name,
                "duration_days": days,
                "created_at": str(created).split(".")[0],
                "expires_at": exp_str,
                "status": display_status
            })
        return result

    def revoke_license(self, key: str) -> bool:
        conn, db_type = get_db()
        cursor = conn.cursor()
        if db_type == "postgres":
            cursor.execute("UPDATE licenses SET status = 'revoked' WHERE license_key = %s", (key,))
        else:
            cursor.execute("UPDATE licenses SET status = 'revoked' WHERE license_key = ?", (key,))
        changed = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return changed

    def delete_license(self, license_id: int) -> bool:
        conn, db_type = get_db()
        cursor = conn.cursor()
        if db_type == "postgres":
            cursor.execute("DELETE FROM licenses WHERE id = %s", (license_id,))
        else:
            cursor.execute("DELETE FROM licenses WHERE id = ?", (license_id,))
        changed = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return changed
