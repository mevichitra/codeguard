# Fixture: CG-SEC-005 safe
# This file MUST NOT trigger CG-SEC-005.

import subprocess


def run_literal_command() -> str:
    # SAFE: literal string with shell=True (no injection vector)
    result = subprocess.run("ls -la", shell=True, capture_output=True, text=True)
    return result.stdout


def git_checkout_safe(branch: str) -> None:
    # SAFE: list form — shell=False (default), no injection
    subprocess.call(["git", "checkout", branch])


def run_with_popen_safe(directory: str) -> None:
    # SAFE: list form, no shell
    proc = subprocess.Popen(["ls", "-la", directory])
    proc.wait()


def check_output_safe(filename: str) -> bytes:
    # SAFE: list form, shell=False explicitly
    return subprocess.check_output(["cat", filename], shell=False)


def run_with_shell_false(cmd: str) -> None:
    # SAFE: shell=False explicitly — even with a variable, no shell injection
    subprocess.run(cmd, shell=False)
