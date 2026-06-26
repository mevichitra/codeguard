# CG-SEC-005 tn sample 3: literal command with shell=True (safe)
import subprocess

# SAFE: literal string with no user input
subprocess.run("ls -la /tmp", shell=True)
