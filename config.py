"""
config.py - all settings for ElderFall in one place.
"""
import os

# ---------- Camera ----------
CAMERA_SOURCE = 0            # 0 = default webcam, or a video file path / IP camera URL
FRAME_WIDTH = 640
FRAME_HEIGHT = 480

# ---------- Fall detection thresholds ----------
TORSO_ANGLE_LYING = 60       # degrees from vertical; above this the body is "horizontal"
ASPECT_RATIO_LYING = 1.2     # body box width / height; above this = lying
DROP_SPEED_THRESHOLD = 0.6   # hip drop in normalized units per second (sudden fall)
CONFIRM_SECONDS = 5          # person must stay down this long before alert
ALERT_COOLDOWN = 60          # seconds before another alert can be sent
MIN_VISIBILITY = 0.5         # ignore landmarks the model is not confident about

# ---------- Alerts: Mobile SMS API ----------
EMERGENCY_PHONE_NUMBER = "+91XXXXXXXXXX"  # Replace with your phone number
SMS_API_URL = "https://api.your-sms-provider.com/send"  # Replace with your SMS gateway endpoint

# ---------- Alerts: Email (optional) ----------
EMAIL_ENABLED = False
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_USER = os.getenv("EMAIL_USER", "")
EMAIL_PASS = os.getenv("EMAIL_PASS", "")      # use an app password, not your real one
EMAIL_TO = os.getenv("EMAIL_TO", "")

# ---------- Output ----------
SNAPSHOT_DIR = "snapshots"
LOG_FILE = "events.csv"
"""
config.py - paths for the ElderFall website (Vercel).
(Your detector keeps its own full config.py. Do not replace it with this one.)
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SNAPSHOT_DIR = os.path.join(BASE_DIR, "snapshots")
LOG_FILE = os.path.join(BASE_DIR, "events.csv")
