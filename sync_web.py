"""
sync_web.py - copy your fall events + photos into the website folder and push to GitHub.
Vercel then redeploys automatically and the website shows the new photos.

Run from inside your elderfall (detector) folder, after the camera has captured falls:
    python sync_web.py

Expects the website folder to sit next to this one:
    C:\\Users\\manoh\\elderfall        <- detector (this folder)
    C:\\Users\\manoh\\elderfall-web    <- website (git repo connected to Vercel)
Change WEB_DIR below if yours is somewhere else.
"""
import glob
import os
import shutil
import subprocess
import sys

import config

HERE = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.abspath(os.path.join(HERE, "..", "elderfall-web"))


def git(*args):
    return subprocess.run(["git", *args], cwd=WEB_DIR, capture_output=True, text=True)


def main():
    if not os.path.isdir(os.path.join(WEB_DIR, ".git")):
        sys.exit(f"Website folder not found or not a git repo: {WEB_DIR}")
    if not os.path.exists(config.LOG_FILE):
        sys.exit("No events.csv yet - nothing to publish.")

    shutil.copy2(config.LOG_FILE, os.path.join(WEB_DIR, "events.csv"))

    dest = os.path.join(WEB_DIR, "snapshots")
    os.makedirs(dest, exist_ok=True)
    count = 0
    for path in glob.glob(os.path.join(config.SNAPSHOT_DIR, "*.jpg")):
        shutil.copy2(path, os.path.join(dest, os.path.basename(path)))
        count += 1
    print(f"Copied events.csv and {count} photo(s) to {WEB_DIR}")

    git("add", "-A")
    if not git("status", "--porcelain").stdout.strip():
        print("Nothing new to publish.")
        return
    git("commit", "-m", "Update fall events and snapshots")
    out = git("push")
    print(out.stdout or out.stderr)
    print("Done. Vercel will redeploy in about a minute.")


if __name__ == "__main__":
    main()
