import subprocess


def backup(request):
    target = request.POST.get("target", "")
    subprocess.check_output("rsync -a data/ " + target, shell=True)
