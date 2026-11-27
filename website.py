"""
website.py - ElderFall dashboard (add-on, does not modify the detector).

Run from inside the elderfall folder, in a second terminal:
    python -m pip install flask
    python website.py

The terminal prints the exact addresses to open (always starting with http://).
Optional password:  set WEB_PASSWORD=yourpassword  (username: admin)
Optional port:      set WEB_PORT=5001
"""
import csv
import os
import socket
from datetime import datetime

from flask import Flask, Response, abort, render_template_string, request, send_from_directory

import config

app = Flask(__name__)
MAX_PHOTOS = 5
PASSWORD = os.getenv("WEB_PASSWORD", "")
START_PORT = int(os.getenv("WEB_PORT", "5001"))


@app.before_request
def require_login():
    if not PASSWORD:
        return None
    auth = request.authorization
    if auth and auth.username == "admin" and auth.password == PASSWORD:
        return None
    return Response("Login required", 401, {"WWW-Authenticate": 'Basic realm="ElderFall"'})


def read_events():
    """Return all events from events.csv, newest first."""
    if not os.path.exists(config.LOG_FILE):
        return []
    events = []
    try:
        with open(config.LOG_FILE, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                snap = row.get("snapshot") or ""
                row["event"] = row.get("event") or ""
                row["photo"] = os.path.basename(snap) if snap else ""
                row["photo_exists"] = bool(row["photo"]) and os.path.exists(
                    os.path.join(config.SNAPSHOT_DIR, row["photo"]))
                try:
                    dt = datetime.fromisoformat(row["timestamp"])
                    row["pretty_time"] = dt.strftime("%d %b %Y, %I:%M:%S %p")
                except (ValueError, KeyError, TypeError):
                    row["pretty_time"] = row.get("timestamp") or ""
                events.append(row)
    except OSError:
        return []
    events.reverse()
    return events


PAGE = """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{% if refresh %}<meta http-equiv="refresh" content="10">{% endif %}
<title>ElderFall</title>
<style>
  * { box-sizing: border-box; }
  body { margin: 0; font-family: system-ui, Arial, sans-serif; background: #f4f6f8; color: #1d2733; }
  header { background: #1d2733; color: #fff; padding: 14px 20px; display: flex;
           justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }
  header h1 { margin: 0; font-size: 20px; }
  nav a { color: #cfd8e3; margin-left: 16px; text-decoration: none; }
  nav a.active { color: #fff; font-weight: 600; }
  main { max-width: 1100px; margin: 0 auto; padding: 20px 16px; }
  .banner { padding: 16px 20px; border-radius: 10px; margin-bottom: 22px; font-weight: 600; }
  .ok { background: #e3f5e8; color: #1b6b35; }
  .alert { background: #fde5e5; color: #a11d1d; }
  .none { background: #e9edf1; color: #4a5866; }
  h2 { font-size: 17px; margin: 24px 0 10px; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 14px; }
  .card { background: #fff; border-radius: 10px; overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,.1); }
  .card img { width: 100%; height: 150px; object-fit: cover; display: block; background: #ddd; cursor: pointer; }
  .card .meta { padding: 10px 12px; font-size: 13px; }
  .card .meta b { display: block; margin-bottom: 2px; }
  table { width: 100%; border-collapse: collapse; background: #fff; border-radius: 10px; overflow: hidden;
          box-shadow: 0 1px 4px rgba(0,0,0,.1); }
  th, td { padding: 10px 12px; text-align: left; font-size: 14px; border-bottom: 1px solid #eef0f3; }
  th { background: #f0f3f6; }
  .tag { padding: 2px 8px; border-radius: 20px; font-size: 12px; font-weight: 600; }
  .tag.alert { background: #fde5e5; color: #a11d1d; }
  .tag.ok { background: #e3f5e8; color: #1b6b35; }
  .empty { color: #6b7886; padding: 20px 0; }
  a.thumb { color: #1565c0; }
  #lightbox { display: none; position: fixed; inset: 0; background: rgba(0,0,0,.85);
              align-items: center; justify-content: center; z-index: 10; }
  #lightbox img { max-width: 92%; max-height: 92%; border-radius: 8px; }
</style>
</head>
<body>
<header>
  <h1>ElderFall Monitor</h1>
  <nav>
    <a href="/" class="{{ 'active' if page == 'home' }}">Dashboard</a>
    <a href="/history" class="{{ 'active' if page == 'history' }}">History</a>
  </nav>
</header>
<main>
{% if page == 'home' %}
  {% if latest %}
    <div class="banner alert">Last fall alert: {{ latest.pretty_time }}</div>
  {% else %}
    <div class="banner none">No fall alerts recorded yet.</div>
  {% endif %}

  <h2>Latest {{ max_photos }} snapshots</h2>
  {% if photos %}
    <div class="grid">
      {% for e in photos %}
        <div class="card">
          <img src="/snapshots/{{ e.photo }}" alt="Fall snapshot" onclick="openBox(this.src)">
          <div class="meta"><b>Fall alert</b>{{ e.pretty_time }}</div>
        </div>
      {% endfor %}
    </div>
  {% else %}
    <p class="empty">No snapshots yet. They appear here after the detector sends an alert.</p>
  {% endif %}
{% else %}
  <h2>All events ({{ events|length }})</h2>
  {% if events %}
    <table>
      <tr><th>Time</th><th>Event</th><th>Snapshot</th></tr>
      {% for e in events %}
        <tr>
          <td>{{ e.pretty_time }}</td>
          <td>
            {% if e.event == 'FALL_ALERT_SENT' %}<span class="tag alert">Alert sent</span>
            {% elif e.event == 'ALERT_CANCELLED_BY_USER' %}<span class="tag ok">Cancelled by user</span>
            {% else %}{{ e.event }}{% endif %}
          </td>
          <td>{% if e.photo_exists %}<a class="thumb" href="#" onclick="openBox('/snapshots/{{ e.photo }}');return false;">View photo</a>{% else %}-{% endif %}</td>
        </tr>
      {% endfor %}
    </table>
  {% else %}
    <p class="empty">No events yet.</p>
  {% endif %}
{% endif %}
</main>
<div id="lightbox" onclick="this.style.display='none'"><img id="lbimg" alt=""></div>
<script>
  function openBox(src) {
    document.getElementById('lbimg').src = src;
    document.getElementById('lightbox').style.display = 'flex';
  }
</script>
</body>
</html>
"""


@app.route("/")
def home():
    alerts = [e for e in read_events() if e.get("event") == "FALL_ALERT_SENT"]
    photos = [e for e in alerts if e["photo_exists"]][:MAX_PHOTOS]
    return render_template_string(PAGE, page="home", refresh=True, max_photos=MAX_PHOTOS,
                                  latest=alerts[0] if alerts else None, photos=photos)


@app.route("/history")
def history():
    return render_template_string(PAGE, page="history", refresh=False, events=read_events())


@app.route("/snapshots/<path:filename>")
def snapshot(filename):
    folder = os.path.abspath(config.SNAPSHOT_DIR)
    return send_from_directory(folder, filename)


@app.route("/favicon.ico")
def favicon():
    return ("", 204)


def port_is_free(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


def lan_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except OSError:
        return None


if __name__ == "__main__":
    port = next((p for p in range(START_PORT, START_PORT + 10) if port_is_free(p)), None)
    if port is None:
        raise SystemExit(f"No free port found between {START_PORT} and {START_PORT + 9}.")

    print("\n" + "=" * 56)
    print(" ElderFall website is starting. Open ONE of these:")
    print(f"   This computer : http://localhost:{port}")
    ip = lan_ip()
    if ip:
        print(f"   Phone (same Wi-Fi): http://{ip}:{port}")
    print(" Use http:// (NOT https://). Press Ctrl+C to stop.")
    print("=" * 56 + "\n")

    app.run(host="0.0.0.0", port=port, debug=False)
