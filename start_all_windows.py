# start_all.py
# Robust starter script for Windows (opens new cmd windows for each service).
# - Auto-detects if services live directly under CWD or under a "tavernAI" subfolder.
# - Uses backend/venv\Scripts\python.exe -m uvicorn if a venv exists there (avoids 'uvicorn' not recognized)
# - Keeps FORCE_KILL option that will taskkill PIDs using the port (dangerous)
# Usage: python start_all.py

import subprocess
import os
import socket
import sys
import time
import shutil

# ---------- CONFIG ----------
FORCE_KILL = False  # set True to forcibly kill processes using the required ports
SERVICES = {
    "backend": {
        "dir": "backend",
        # this cmd will be computed dynamically to prefer backend/venv python
        "cmd": None,
        "port": 8000
    },
    "waiter": {
        "dir": "waiter-ui",
        "cmd": r'npm run dev -- --host 0.0.0.0 --port 5173',
        "port": 5173
    },
    "grill": {
        "dir": "grill-ui",
        "cmd": r'npm run dev -- --host 0.0.0.0 --port 5174',
        "port": 5174
    },
    "kitchen": {
        "dir": "kitchen-ui",
        "cmd": r'npm run dev -- --host 0.0.0.0 --port 5175',
        "port": 5175
    }
}
# ---------- /CONFIG ----------

# Where the script lives (useful when started from another cwd)
SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))

def find_repo_root():
    """
    Return a directory that contains any of the expected service folders.
    Strategy:
      - If CWD contains required folders, use CWD.
      - Else if script-folder contains required folders, use script-folder.
      - Else if there is a 'tavernAI' child subfolder in CWD or script-folder, try that.
      - Fall back to SCRIPT_DIR.
    """
    candidates = [os.getcwd(), SCRIPT_DIR]
    checked = set()
    for base in candidates:
        if base in checked: continue
        checked.add(base)
        # if base already looks like repo root (has backend folder), return it
        if all(os.path.isdir(os.path.join(base, SERVICES[s]['dir'])) for s in SERVICES):
            return base
        # try child 'tavernAI' or 'backend' siblings
        tav = os.path.join(base, "tavernAI")
        if os.path.isdir(tav) and all(os.path.isdir(os.path.join(tav, SERVICES[s]['dir'])) for s in SERVICES):
            return tav
    # fallback: search up a few parents from SCRIPT_DIR
    p = SCRIPT_DIR
    for _ in range(4):
        p = os.path.dirname(p)
        if p and all(os.path.isdir(os.path.join(p, SERVICES[s]['dir'])) for s in SERVICES):
            return p
    # last resort: SCRIPT_DIR
    return SCRIPT_DIR

ROOT = find_repo_root()

def is_port_free(port, host='0.0.0.0'):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, port))
        s.close()
        return True
    except OSError:
        return False

def find_pids_using_port(port):
    """Return a set of PIDs using the given port on Windows by parsing netstat -ano output."""
    try:
        out = subprocess.check_output(['netstat', '-ano'], universal_newlines=True, stderr=subprocess.DEVNULL)
    except Exception:
        return set()
    pids = set()
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 5:
            local = parts[1]
            pid = parts[-1]
            if ':' in local:
                try:
                    p = int(local.rsplit(':', 1)[1])
                except Exception:
                    continue
                if p == port:
                    try:
                        pids.add(int(pid))
                    except Exception:
                        pass
    return pids

def kill_pids(pids):
    for pid in pids:
        try:
            subprocess.check_call(['taskkill', '/PID', str(pid), '/F'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"  -> killed PID {pid}")
        except Exception as e:
            print(f"  -> failed to kill PID {pid}: {e}")

def start_cmd_in_new_window(command, workdir):
    # Use start "" cmd /k "cd /d <workdir> && <command>"
    abs_dir = os.path.abspath(workdir)
    # Escape double quotes in path
    abs_dir_escaped = abs_dir.replace('"', r'\"')
    cmd_line = f'start "" cmd /k "cd /d \"{abs_dir_escaped}\" && {command}"'
    subprocess.Popen(cmd_line, shell=True)

def detect_backend_python(backend_dir):
    """
    If backend/venv exists and has a python.exe, return its path.
    Otherwise return None.
    """
    venv_python = os.path.join(backend_dir, "venv", "Scripts", "python.exe")
    if os.path.isfile(venv_python):
        return venv_python
    # also check for .venv
    venv2 = os.path.join(backend_dir, ".venv", "Scripts", "python.exe")
    if os.path.isfile(venv2):
        return venv2
    # no venv found
    return None

def prepare_backend_command(backend_dir):
    # prefer backend venv python if present (avoids relying on activate)
    py = detect_backend_python(backend_dir)
    if py:
        # use -m uvicorn with that python
        safe_py = f'"{py}"'
        cmd = f'{safe_py} -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000'
        return cmd
    # else fallback to system python that runs this script
    sys_py = sys.executable or "python"
    safe_sys_py = f'"{sys_py}"'
    return f'{safe_sys_py} -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000'

def main():
    print("Starting services with fixed ports (backend:8000, waiter:5173, grill:5174, kitchen:5175)\n")
    print(f"Detected repository root: {ROOT}\n")

    # fill backend command dynamically
    for name, info in SERVICES.items():
        if name == "backend" and not info.get("cmd"):
            backend_dir = os.path.join(ROOT, info["dir"])
            info["cmd"] = prepare_backend_command(backend_dir)

    for name, info in SERVICES.items():
        port = info.get("port")
        cmd = info.get("cmd")
        d = info.get("dir")
        abs_dir = os.path.join(ROOT, d)
        print(f"[{name}] dir={abs_dir} port={port}")

        if not os.path.isdir(abs_dir):
            print(f"  ⚠️  directory not found: {abs_dir} - skipping")
            print("")
            continue

        if is_port_free(port):
            print(f"  ✅ port {port} is free, launching...")
            start_cmd_in_new_window(cmd, abs_dir)
            time.sleep(0.45)
        else:
            pids = find_pids_using_port(port)
            if pids:
                print(f"  ❌ port {port} appears to be in use by PIDs: {', '.join(map(str,pids))}")
            else:
                print(f"  ❌ port {port} appears to be in use (couldn't determine PID)")

            if FORCE_KILL and pids:
                print(f"  ⚠️  FORCE_KILL is True — attempting to kill PIDs using port {port} ...")
                kill_pids(pids)
                time.sleep(0.6)
                if is_port_free(port):
                    print(f"  ✅ port {port} now free after killing. launching...")
                    start_cmd_in_new_window(cmd, abs_dir)
                    time.sleep(0.45)
                else:
                    print(f"  ❌ still not free after kill attempt. Skipping start for {name}.")
            else:
                print(f"  ℹ️  Not starting {name}. Free the port or enable FORCE_KILL in this script to terminate the occupying process.")
        print("")

    print("Done. Check each new terminal window. If a UI fails to start, open its terminal to read the error logs.")

if __name__ == "__main__":
    main()
