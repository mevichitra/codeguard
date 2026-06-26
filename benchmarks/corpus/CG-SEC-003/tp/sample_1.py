# CG-SEC-003 tp sample 1: eval on user input
def calculate(expression):
    # VULNERABLE
    return eval(expression)

result = calculate(input("Enter math: "))
