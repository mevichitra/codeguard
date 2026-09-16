# CG-SEC-003 tn sample 2: using json for safe evaluation (no eval/exec)
import json

def evaluate(expr_str):
    # SAFE: json.loads only parses JSON literals, no code execution
    return json.loads(expr_str)

result = evaluate('[1, 2, 3]')
