import subprocess,time,hashlib
from pathlib import Path
from datetime import datetime,timezone

ROOT=Path(r"G:\bet_tracker\app")
PYTHON=ROOT/".venv"/"Scripts"/"python.exe"
LOG=Path(r"G:\bet_tracker\website_prod_files\waitress_supervisor.log")
ERR=Path(r"G:\bet_tracker\website_prod_files\waitress_stderr.log")
EXCLUDE={".venv",".git","__pycache__","frontend"}
TYPES={".py",".html",".jinja",".jinja2",".json",".yaml",".yml",".ini",".toml",".txt"}

def log(s):
    with LOG.open("a",encoding="utf-8") as f:
        f.write(datetime.now(timezone.utc).isoformat()+" "+s+"\n")

def sig():
    h=hashlib.sha256()
    for p in sorted(ROOT.rglob("*")):
        if not p.is_file(): continue
        r=p.relative_to(ROOT)
        if any(x in EXCLUDE for x in r.parts): continue
        if p.suffix.lower() not in TYPES and p.name!=".env": continue
        try:
            s=p.stat()
            h.update(str(r).encode())
            h.update(str(s.st_size).encode())
            h.update(str(s.st_mtime_ns).encode())
        except OSError: pass
    return h.hexdigest()

def start():
    e=ERR.open("a",encoding="utf-8")
    p=subprocess.Popen(
        [str(PYTHON),"-m","waitress",
         "--listen=127.0.0.1:8000",
         "--trusted-proxy=127.0.0.1",
         "--trusted-proxy-headers=x-forwarded-proto",
         "config.wsgi:application"],
        cwd=str(ROOT),stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,stderr=e,
        creationflags=0x08000000)
    log("Started Waitress PID "+str(p.pid))
    return p,e

def stop(p,e):
    if p and p.poll() is None:
        log("Stopping Waitress PID "+str(p.pid))
        try:
            p.terminate()
            p.wait(timeout=8)
        except Exception:
            try: p.kill()
            except Exception: pass
    try: e.close()
    except Exception: pass

log("Supervisor started")
current=sig()
p=None
eh=None

while True:
    if p is None or p.poll() is not None:
        if p is not None: log("Waitress exited")
        p,eh=start()
        time.sleep(3)
    if sig()!=current:
        current=sig()
        log("Application/template change detected")
        stop(p,eh)
        time.sleep(1)
        p,eh=start()
        time.sleep(3)
    time.sleep(2)