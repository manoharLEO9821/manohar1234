"""
alert_service.py - sends emergency SMS alerts + optional email
and logs every event to a CSV file.
Alerts run in a background thread so the video feed never freezes.
"""
import csv
import os
import smtplib
import threading
from datetime import datetime
from email.message import EmailMessage

import cv2
import requests

import config

try:
    from auto_sync import push_to_github as _push_to_github
except ImportError:
    _push_to_github = None


def _save_snapshot(frame):
    os.makedirs(config.SNAPSHOT_DIR, exist_ok=True)
    name = datetime.now().strftime("fall_%Y%m%d_%H%M%S.jpg")
    path = os.path.join(config.SNAPSHOT_DIR, name)
    cv2.imwrite(path, frame)
    return path


def _to_relative_snapshot_path(snapshot_path):
    if not snapshot_path:
        return ""
    filename = os.path.basename(str(snapshot_path).replace("\\", "/"))
    snap_folder = os.path.basename(os.path.normpath(config.SNAPSHOT_DIR)) or "snapshots"
    return f"{snap_folder}/{filename}"


def _log_event(event, snapshot_path=""):
    rel_snapshot = _to_relative_snapshot_path(snapshot_path)
    log_dir = os.path.dirname(os.path.abspath(config.LOG_FILE))
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    file_exists = os.path.exists(config.LOG_FILE) and os.path.getsize(config.LOG_FILE) > 0
    needs_newline = False
    if file_exists:
        with open(config.LOG_FILE, "rb") as f_bin:
            f_bin.seek(-1, os.SEEK_END)
            if f_bin.read(1) not in (b"\n", b"\r"):
                needs_newline = True

    with open(config.LOG_FILE, "a", newline="", encoding="utf-8") as f:
        if needs_newline:
            f.write("\n")
        writer = csv.writer(f, lineterminator="\n")
        if not file_exists:
            writer.writerow(["timestamp", "event", "snapshot"])
        writer.writerow([datetime.now().isoformat(timespec="seconds"), event, rel_snapshot])


def _send_sms(message):
    if not config.EMERGENCY_PHONE_NUMBER:
        print("[alert] Emergency phone number not configured, skipping SMS.")
        return

    payload = {
        "phone": config.EMERGENCY_PHONE_NUMBER,
        "message": message
    }
    try:
        r = requests.post(config.SMS_API_URL, json=payload, timeout=15)
        print("[alert] SMS API status:", r.status_code)
    except requests.RequestException as e:
        print("[alert] SMS failed:", e)


def _send_email(path, message):
    if not (config.EMAIL_ENABLED and config.EMAIL_USER and config.EMAIL_TO):
        return
    try:
        msg = EmailMessage()
        msg["Subject"] = "ElderFall emergency alert"
        msg["From"] = config.EMAIL_USER
        msg["To"] = config.EMAIL_TO
        msg.set_content(message)
        with open(path, "rb") as f:
            msg.add_attachment(f.read(), maintype="image", subtype="jpeg",
                               filename=os.path.basename(path))
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as server:
            server.starttls()
            server.login(config.EMAIL_USER, config.EMAIL_PASS)
            server.send_message(msg)
        print("[alert] Email sent.")
    except Exception as e:
        print("[alert] Email failed:", e)


def _trigger_git_sync(msg):
    if _push_to_github is None:
        return
    try:
        _push_to_github(msg)
    except Exception as e:
        print("[alert] Git sync skipped:", e)


def send_emergency_alert(frame):
    """Save a snapshot, log it, and notify caregivers via SMS without blocking the video loop."""
    path = _save_snapshot(frame.copy())
    stamp = datetime.now().strftime("%d %b %Y, %H:%M:%S")
    message = f"ElderFall ALERT: possible fall detected at {stamp}. Please check immediately."
    _log_event("FALL_ALERT_SENT", path)

    threading.Thread(target=_send_sms, args=(message,), daemon=True).start()
    threading.Thread(target=_send_email, args=(path, message), daemon=True).start()
    threading.Thread(
        target=_trigger_git_sync,
        args=(f"Fall alert {datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}",),
        daemon=True,
    ).start()


def log_cancelled():
    _log_event("ALERT_CANCELLED_BY_USER")
    threading.Thread(
        target=_trigger_git_sync,
        args=(f"Alert cancelled {datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}",),
        daemon=True,
    ).start()