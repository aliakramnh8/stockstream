import sqlite3
import os
import uuid
import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "licenses.db"))

ADMIN_PASSWORD_HASH = hashlib.sha256("admin123".encode()).hexdigest()

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
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
    # Delete any master keys so no one gets free master access
    cursor.execute("DELETE FROM licenses WHERE license_key = 'SS-MASTER-2026'")
    conn.commit()
    conn.close()

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

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
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

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT license_key, client_name, duration_days, expires_at, status, device_id
            FROM licenses WHERE license_key = ?
        """, (clean_key,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return {"valid": False, "message": "Invalid License Key. Please enter a valid purchased key."}

        license_key, client_name, duration_days, expires_at_str, status, saved_device_id = row

        if status != 'active':
            return {"valid": False, "message": "This license key has been revoked/deactivated."}

        try:
            expires_at = datetime.strptime(expires_at_str, "%Y-%m-%d %H:%M:%S")
            now = datetime.now()
            if now > expires_at:
                return {"valid": False, "message": f"License expired on {expires_at_str}. Please renew."}

            days_remaining = max(0, (expires_at - now).days)
            return {
                "valid": True,
                "client_name": client_name,
                "expires_at": expires_at_str,
                "days_remaining": days_remaining,
                "license_key": license_key
            }
        except Exception as e:
            return {"valid": False, "message": f"Error validating license: {e}"}

    def list_all_licenses(self) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(DB_PATH)
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
                exp_dt = datetime.strptime(expires, "%Y-%m-%d %H:%M:%S")
                is_expired = now > exp_dt
            except:
                is_expired = False

            display_status = "expired" if is_expired and status == "active" else status
            result.append({
                "id": id_,
                "license_key": key,
                "client_name": name,
                "duration_days": days,
                "created_at": created,
                "expires_at": expires,
                "status": display_status
            })
        return result

    def revoke_license(self, key: str) -> bool:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE licenses SET status = 'revoked' WHERE license_key = ?", (key,))
        changed = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return changed

    def delete_license(self, license_id: int) -> bool:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM licenses WHERE id = ?", (license_id,))
        changed = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return changed
