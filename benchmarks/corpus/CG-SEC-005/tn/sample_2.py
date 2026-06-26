# CG-SEC-005 tn sample 2: subprocess.run with fixed command (safe)
import subprocess

def check_disk():
    # SAFE: fully static command, list form
    result = subprocess.run(["df", "-h"], capture_output=True)
    return result.stdout.decode()
