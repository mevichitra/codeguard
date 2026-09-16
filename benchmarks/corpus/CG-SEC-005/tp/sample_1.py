# CG-SEC-005 tp sample 1: shell=True with f-string
import subprocess

def ping_host(host):
    # VULNERABLE
    subprocess.run(f"ping -c 1 {host}", shell=True, capture_output=True)
    return host

ping_host("8.8.8.8")
