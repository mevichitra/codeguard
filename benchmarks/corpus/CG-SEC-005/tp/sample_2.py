# CG-SEC-005 tp sample 2: shell=True with concatenation
import subprocess

def delete_file(path):
    # VULNERABLE
    subprocess.call("rm -f " + path, shell=True)

delete_file("/tmp/test.txt")
