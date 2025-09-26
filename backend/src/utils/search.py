def sanitize_query(q: str) -> str:
    q = (q or "").strip()

    return f"%{q.lower()}%"