"""Timestamp formatting utilities."""

from datetime import datetime, timedelta


def format_timestamp(iso_timestamp: str, relative: bool = False) -> str:
    """
    Format ISO 8601 timestamp to readable format.

    Args:
        iso_timestamp: ISO 8601 formatted timestamp string
        relative: If True, show relative time (e.g., "2 hours ago")
                 If False, show absolute time (e.g., "2025-11-13 18:45:40")

    Returns:
        Human-readable timestamp

    Examples:
        format_timestamp("2025-11-13T18:45:40.572549")
        # "2025-11-13 18:45:40"

        format_timestamp("2025-11-13T18:45:40.572549", relative=True)
        # "2 hours ago"
    """
    try:
        dt = datetime.fromisoformat(iso_timestamp)

        if relative:
            return _format_relative_time(dt)
        else:
            return dt.strftime("%Y-%m-%d %H:%M:%S")

    except (ValueError, AttributeError):
        # Return original if parsing fails
        return iso_timestamp


def _format_relative_time(dt: datetime) -> str:
    """
    Format datetime as relative time in compact format (e.g., "2h ago").

    Matches the style of `make recent`:
    - Seconds: "30s ago"
    - Minutes: "15m ago"
    - Hours: "2h ago"
    - Days: "5d ago"

    Args:
        dt: datetime object to format

    Returns:
        Compact relative time string
    """
    now = datetime.now()
    diff = now - dt

    # Future times
    if diff.total_seconds() < 0:
        diff = -diff
        suffix = "from now"
    else:
        suffix = "ago"

    # Calculate time units
    seconds = int(diff.total_seconds())
    minutes = seconds // 60
    hours = minutes // 60
    days = diff.days

    # Format based on magnitude (compact format like make recent)
    if seconds < 60:
        return f"{seconds}s {suffix}"
    elif minutes < 60:
        return f"{minutes}m {suffix}"
    elif hours < 24:
        return f"{hours}h {suffix}"
    else:
        return f"{days}d {suffix}"
