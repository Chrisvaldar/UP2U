def truncate_log(text: str, max_len: int = 80) -> str:
    if len(text) <= max_len:
        return text
    return f"Output ({max_len}/{len(text)} char): " + text[:max_len]
