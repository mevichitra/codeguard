# CG-SEC-003 tp sample 3: compile + exec on user input
def compile_and_run(source):
    # VULNERABLE
    code = compile(source, "<user>", "exec")
    exec(code)

compile_and_run("print('hello')")
