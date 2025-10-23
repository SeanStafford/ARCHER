def truncate_display(text: str, max_len: int) -> str:
    return text if len(text) <= max_len else text[: max_len - 3] + "..."
