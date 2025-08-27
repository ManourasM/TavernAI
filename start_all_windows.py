# start_all.py
# Run from the repository root that contains the folders:
# backend/, waiter-ui/, grill-ui/, kitchen-ui/
#
# Usage: python start_all.py
# Set FORCE_KILL = True if you want the script to forcibly kill whatever is using the port (dangerous).

import subprocess
import os
import socket
import sys
import time
import subprocess

# ---------- CONFIG ----------
FORCE_KILL = False  # set to True if you want this script to kill processes already using required ports
SERVICES = {
    "backend": {
        "dir": "backend",
        "cmd": r'call venv\Scripts\activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000',
        "port": 8000
    },
    "waiter": {
        "dir": "waiter-ui",
        # explicit host + port so Vite will not try other ports
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

ROOT = os.path.abspath(os.getcwd())

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
        # typical line: TCP    0.0.0.0:5173      0.0.0.0:0     LISTENING      1234
        if len(parts) >= 5:
            proto = parts[0]
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
    # Make sure to use absolute path
    abs_dir = os.path.abspath(workdir)
    cmd = f'start "" cmd /k "cd /d {abs_dir} && {command}"'
    subprocess.Popen(cmd, shell=True)

def main():
    print("Starting services with fixed ports (backend:8000, waiter:5173, grill:5174, kitchen:5175)\n")
    for name, info in SERVICES.items():
        port = info.get("port")
        cmd = info.get("cmd")
        d = info.get("dir")
        print(f"[{name}] dir={d} port={port}")

        if not os.path.isdir(os.path.join(ROOT, d)):
            print(f"  ⚠️  directory not found: {os.path.join(ROOT, d)} - skipping")
            continue

        if is_port_free(port):
            print(f"  ✅ port {port} is free, launching...")
            start_cmd_in_new_window(cmd, os.path.join(ROOT, d))
            # small delay so multiple 'start' don't race
            time.sleep(0.4)
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
                # re-check
                if is_port_free(port):
                    print(f"  ✅ port {port} now free after killing. launching...")
                    start_cmd_in_new_window(cmd, os.path.join(ROOT, d))
                    time.sleep(0.4)
                else:
                    print(f"  ❌ still not free after kill attempt. Skipping start for {name}.")
            else:
                print(f"  ℹ️  Not starting {name}. Free the port or enable FORCE_KILL in this script to terminate the occupying process.")
        print("")

    print("Done. Check each new terminal window. If a UI fails to start, open its terminal to read the error logs.")

if __name__ == "__main__":
    main()
