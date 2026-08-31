# Fixture: CG-SEC-003 safe
# This file MUST NOT trigger CG-SEC-003.

import ast


# SAFE: eval on a string literal (code smell but not the dangerous case)
result = eval("1 + 1")


# SAFE: ast.literal_eval — safe alternative for parsing data
def parse_config_value(raw: str) -> object:
    return ast.literal_eval(raw)


# SAFE: dispatch via dict — the right way to handle dynamic behavior
HANDLERS = {
    "add": lambda x, y: x + y,
    "sub": lambda x, y: x - y,
}


def dispatch(op: str, x: int, y: int) -> int:
    handler = HANDLERS.get(op)
    if handler is None:
        raise ValueError(f"Unknown operation: {op!r}")
    return handler(x, y)
