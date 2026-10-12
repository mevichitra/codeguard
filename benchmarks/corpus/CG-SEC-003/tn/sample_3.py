# CG-SEC-003 tn sample 3: pre-compiled template (safe, no user input)
import string

TEMPLATE = string.Template("Hello, \$name!")

def greet(name):
    return TEMPLATE.safe_substitute(name=name)
