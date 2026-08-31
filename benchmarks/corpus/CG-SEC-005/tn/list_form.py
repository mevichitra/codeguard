import subprocess
def r(branch): subprocess.run(["git", "checkout", branch])
