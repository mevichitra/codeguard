# Fixture: CG-SEC-005 vulnerable
# This file MUST trigger CG-SEC-005 (subprocess shell=True with dynamic command).

import subprocess


def run_user_command(cmd: str) -> str:
    # VULNERABLE: f-string command + shell=True
    result = subprocess.run(f"echo {cmd}", shell=True, capture_output=True, text=True)
    return result.stdout


def git_checkout(branch: str) -> None:
    # VULNERABLE: concatenated command + shell=True
    subprocess.call("git checkout " + branch, shell=True)


def run_with_popen(user_arg: str) -> None:
    # VULNERABLE: Popen with shell=True and variable
    proc = subprocess.Popen(f"ls {user_arg}", shell=True)
    proc.wait()


def check_output_dynamic(cmd: str) -> bytes:
    # VULNERABLE: check_output + shell=True + variable
    return subprocess.check_output(cmd, shell=True)
