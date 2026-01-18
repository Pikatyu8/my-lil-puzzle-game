OPERATORS = {
    "==": lambda a, b: a == b, ">=": lambda a, b: a >= b, "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b, "<": lambda a, b: a < b, "!=": lambda a, b: a != b,
    "=": lambda a, b: a == b,
}

OP_SYMBOLS = {"==": "=", ">=": "≥", "<=": "≤", ">": ">", "<": "<", "!=": "≠"}


def get_operator(op, default_op):
    return OPERATORS.get(op, OPERATORS[default_op])
