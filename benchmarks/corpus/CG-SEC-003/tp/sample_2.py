# CG-SEC-003 tp sample 2: exec on dynamic code
def run_script(code_string):
    # VULNERABLE
    exec(code_string)

run_script("import os; os.system('ls')")
