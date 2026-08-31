import subprocess
filename = input("file: ")
subprocess.call(f"cat {filename}", shell=True)
