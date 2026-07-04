def truncate_log(text: str, max_len: int = 80) -> str:
    """
    Truncate long text for safe logging without dumping full payloads.

    Args:
        text: Raw string to log, such as an API response body.
        max_len: Maximum number of characters to include. Defaults to 80.

    Returns:
        The original text if within max_len, otherwise a prefixed truncation.
    """
    if len(text) <= max_len:
        return text
    return f"Output ({max_len}/{len(text)} char): " + text[:max_len]
