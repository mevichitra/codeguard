import subprocess


def backup(target):
    # target is a parameter of a plain function, not request data
    subprocess.check_output(["rsync", "-a", "data/", target])
