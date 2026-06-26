# CG-SEC-005 tp sample 3: subprocess.run with shell=True and dynamic cmd
import subprocess

def run_command(cmd):
    # VULNERABLE: shell=True with dynamic command
    subprocess.run(cmd, shell=True)
