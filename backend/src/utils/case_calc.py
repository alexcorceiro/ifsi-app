import re

def parse_value_unit(text: str):
    if not text:
        return None, None
    t = text.strip().lower().replace(",",".")
    m = re.search(r"(-?\d+(\.\d+)?)\s*([a-zµ]+)?", t)
    if not m:
        return None, None
    value = float(m.group(1))
    unit = (m.group(3) or "").strip()
    return value, unit or None

def to_mg(value: float, unit: str):
    unit = (unit or "").lower()
    if unit in ("mg", "milligramme", "milligrammes"):
        return value
    if unit in ("g", "gramme", "grammes"):
        return value * 1000.0
    return None 