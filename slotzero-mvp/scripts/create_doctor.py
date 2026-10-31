"""Provision a doctor account without exposing public doctor registration."""
from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import app as slotzero  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a SlotZero doctor account")
    parser.add_argument("--name", required=True, help="Doctor's display name")
    parser.add_argument("--email", required=True, help="Doctor's login email")
    parser.add_argument("--specialization", required=True, help="Doctor's specialization")
    parser.add_argument("--timezone", required=True, choices=slotzero.ALLOWED_ZONES, help="Doctor's IANA time zone")
    args = parser.parse_args()

    password = getpass.getpass("Initial password (minimum 10 characters): ")
    confirm = getpass.getpass("Confirm password: ")
    if len(password) < 10:
        print("Error: use at least 10 characters.", file=sys.stderr)
        return 2
    if password != confirm:
        print("Error: passwords do not match.", file=sys.stderr)
        return 2

    slotzero.init_db()
    try:
        with slotzero.transaction(immediate=True) as conn:
            cur = conn.execute(
                "INSERT INTO users(full_name,email,password_hash,role,timezone,created_at) VALUES(?,?,?,'doctor',?,?)",
                (args.name.strip(), args.email.strip().lower(), slotzero.hash_password(password), args.timezone, slotzero.dt_to_db(slotzero.utc_now())),
            )
            doctor_id = cur.lastrowid
            conn.execute(
                "INSERT INTO doctors(user_id,specialization,bio,consultation_minutes) VALUES(?,?,?,30)",
                (doctor_id, args.specialization.strip(), "", 30),
            )
    except Exception as exc:
        print(f"Could not create doctor: {exc}", file=sys.stderr)
        return 1

    print(f"Created doctor account for {args.name.strip()} ({args.email.strip().lower()}).")
    print("The doctor must sign in and configure weekly working hours before slots become bookable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
