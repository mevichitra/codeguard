# Fixture: CG-SEC-003 vulnerable
# This file MUST trigger CG-SEC-003 (eval/exec on dynamic input).

import sys


def run_user_command(user_input: str) -> None:
    # VULNERABLE: eval on user-controlled string
    eval(user_input)


def execute_script(script: str) -> None:
    # VULNERABLE: exec on a variable
    exec(script)


def dynamic_compile(code_str: str) -> object:
    # VULNERABLE: compile on a non-literal
    return compile(code_str, "<string>", "exec")


def evaluate_expression(expr: str) -> object:
    # VULNERABLE: eval on a method return value
    return eval(expr.strip())
