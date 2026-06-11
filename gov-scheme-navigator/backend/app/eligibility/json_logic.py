from __future__ import annotations

from typing import Any, Dict


def jsonLogic(rules: Any, data: Dict[str, Any]) -> Any:
    """Lightweight JSONLogic evaluator covering common operators used by the engine.

    This supports: var, and, or, !, in, ==, !=, <, >, <=, >=.
    It's intentionally small and permissive — returns False on errors.
    """
    try:
        return _eval(rules, data)
    except Exception:
        return False


def _eval(rules: Any, data: Dict[str, Any]) -> Any:
    # Primitives
    if rules is None or isinstance(rules, (str, int, float, bool)):
        return rules

    # Lists: evaluate each element
    if isinstance(rules, list):
        return [_eval(r, data) for r in rules]

    # Dict: operator form
    if isinstance(rules, dict):
        if not rules:
            return {}
        op, val = next(iter(rules.items()))

        if op == "var":
            # val can be a string or [name, default]
            if isinstance(val, list):
                name = val[0] if val else None
                default = val[1] if len(val) > 1 else None
            else:
                name = val
                default = None
            if name is None or name == "":
                return data
            return data.get(name, default)

        if op == "and":
            return all(bool(_eval(x, data)) for x in val)

        if op == "or":
            return any(bool(_eval(x, data)) for x in val)

        if op == "!":
            return not bool(_eval(val, data))

        if op == "in":
            if not isinstance(val, list) or len(val) < 2:
                return False
            left = _eval(val[0], data)
            right = _eval(val[1], data)
            try:
                return left in right
            except Exception:
                return False

        if op in ("==", "==="):
            a = _eval(val[0], data) if isinstance(val, list) and len(val) > 0 else None
            b = _eval(val[1], data) if isinstance(val, list) and len(val) > 1 else None
            return a == b

        if op in ("!=", "!=="):
            a = _eval(val[0], data) if isinstance(val, list) and len(val) > 0 else None
            b = _eval(val[1], data) if isinstance(val, list) and len(val) > 1 else None
            return a != b

        if op in ("<", ">", "<=", ">="):
            try:
                a = _eval(val[0], data)
                b = _eval(val[1], data)
                if a is None or b is None:
                    return False
                if op == "<":
                    return a < b
                if op == ">":
                    return a > b
                if op == "<=":
                    return a <= b
                if op == ">=":
                    return a >= b
            except Exception:
                return False

        # Unknown operator: evaluate operands and return structure
        return {op: _eval(val, data)}

    # Fallback
    return False
