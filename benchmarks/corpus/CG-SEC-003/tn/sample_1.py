# CG-SEC-003 tn sample 1: ast.literal_eval (safe)
import ast

def safe_eval(expr):
    # SAFE
    return ast.literal_eval(expr)

result = safe_eval("[1, 2, 3]")
