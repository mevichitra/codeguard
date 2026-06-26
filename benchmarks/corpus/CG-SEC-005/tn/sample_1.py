# CG-SEC-005 tn sample 1: subprocess.run with list (safe)
import subprocess

def ping_host(host):
    # SAFE: no shell=True
    subprocess.run(["ping", "-c", "1", host], capture_output=True)
