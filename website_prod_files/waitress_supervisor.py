# BetTracker Waitress supervisor: reload on source change, restart on crash or health failure.
# Single-instance file lock and PID metadata allow the Windows uptime monitor to recover safely.
import hashlib
import json
import msvcrt
import os
import subprocess
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"G:\bet_tracker\app")
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
BASE = Path(r"G:\bet_tracker\website_prod_files")
LOG = BASE / "waitress_supervisor.log"
ERR = BASE / "waitress_stderr.log"
RUNTIME = Path(r"C:\Users\Mat\AppData\Local\BetTrackerMonitor")
LOCK = RUNTIME / "waitress_supervisor.lock"
STATUS = RUNTIME / "waitress_supervisor_status.json"
EXCLUDE = {".venv", ".git", "__pycache__", "frontend"}
TYPES = {".py", ".html", ".jinja", ".jinja2", ".json", ".yaml", ".yml", ".ini", ".toml", ".txt"}
HEALTH_URL = "http://127.0.0.1:8000/healthz"
STARTED_UTC = datetime.now(timezone.utc).isoformat()


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def log(message):
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(utc_now() + " " + message + "\n")


def signature():
    digest = hashlib.sha256()
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        if any(part in EXCLUDE for part in rel.parts):
            continue
        if path.suffix.lower() not in TYPES and path.name != ".env":
            continue
        try:
            stat = path.stat()
            digest.update(str(rel).encode())
            digest.update(str(stat.st_size).encode())
            digest.update(str(stat.st_mtime_ns).encode())
        except OSError:
            continue
    return digest.digest()


def health_ok():
    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=6) as response:
            return response.status == 200
    except Exception:
        return False


def write_status(child=None, child_start=None):
    data = {
        "supervisor_pid": os.getpid(),
        "supervisor_started_utc": STARTED_UTC,
        "heartbeat_utc": utc_now(),
        "waitress_pid": child.pid if child else None,
        "waitress_started_utc": child_start,
    }
    temp = STATUS.with_name(STATUS.name + "." + str(os.getpid()) + ".tmp")
    with temp.open("w", encoding="utf-8") as fh:
        json.dump(data, fh)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(temp, STATUS)


def start():
    fh = ERR.open("a", encoding="utf-8")
    try:
        child = subprocess.Popen(
            [str(PYTHON), "-m", "waitress",
             "--listen=127.0.0.1:8000",
             "--trusted-proxy=127.0.0.1",
             "--trusted-proxy-headers=x-forwarded-proto",
             "config.wsgi:application"],
            cwd=str(ROOT), stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=fh,
            creationflags=0x08000000,
        )
    except Exception:
        fh.close()
        raise
    child_start = utc_now()
    log("Started Waitress PID " + str(child.pid))
    write_status(child, child_start)
    return child, fh, child_start


def stop(child, fh):
    if child is not None and child.poll() is None:
        log("Stopping Waitress tree PID " + str(child.pid))
        # Windows virtualenv Python can spawn an additional interpreter:
        # terminate the entire child tree rather than only the wrapper PID.
        try:
            subprocess.run(["taskkill.exe", "/PID", str(child.pid), "/T", "/F"],
                           timeout=15, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as exc:
            log("WARNING: taskkill failed: " + str(exc))
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            log("WARNING: Waitress wrapper did not exit after taskkill")
    if fh is not None:
        fh.close()


def acquire_lock():
    # Keep an OS file lock for this entire process lifetime.
    handle = LOCK.open("a+b")
    handle.seek(0, os.SEEK_END)
    if handle.tell() < 1:
        handle.write(b"0")
        handle.flush()
    handle.seek(0)
    try:
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        handle.close()
        return None
    return handle


def main():
    if not PYTHON.is_file():
        raise RuntimeError("Python virtual environment missing at " + str(PYTHON))
    locker = acquire_lock()
    if locker is None:
        log("Second supervisor launch blocked by process lock")
        return
    child = None
    stderr = None
    child_start = None
    try:
        log("Supervisor started")
        baseline = signature()
        failed = 0
        last_probe = 0
        last_scan = 0
        while True:
            now = time.monotonic()
            if child is None or child.poll() is not None:
                if child is not None:
                    log("Waitress exited; restarting")
                    stop(child, stderr)
                child, stderr, child_start = start()
                failed = 0
                last_probe = now
                time.sleep(5)
            now = time.monotonic()
            if now - last_probe >= 15:
                last_probe = now
                failed = 0 if health_ok() else failed + 1
                if failed >= 3:
                    log("Health endpoint failed 3 consecutive probes; restarting Waitress")
                    stop(child, stderr)
                    child, stderr, child_start = start()
                    failed = 0
                    time.sleep(5)
                write_status(child, child_start)
            if now - last_scan >= 10:
                last_scan = now
                updated = signature()
                if updated != baseline:
                    baseline = updated
                    log("Application/template change detected")
                    stop(child, stderr)
                    child, stderr, child_start = start()
                    failed = 0
                    time.sleep(5)
            time.sleep(2)
    finally:
        try:
            stop(child, stderr)
        finally:
            # Preserve status on exit so Windows monitor can recover orphans.
            msvcrt.locking(locker.fileno(), msvcrt.LK_UNLCK, 1)
            locker.close()


if __name__ == "__main__":
    main()
