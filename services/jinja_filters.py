def format_number(value):
    try:
        return f"{int(value):,}"
    except (ValueError, TypeError):
        return value

from datetime import datetime

def timeago(value):
    if not value:
        return "—"

    if isinstance(value, str):
        return value  # fallback safety

    now = datetime.utcnow()
    diff = now - value

    seconds = int(diff.total_seconds())
    minutes = seconds // 60
    hours = minutes // 60
    days = hours // 24

    if seconds < 60:
        return "just now"
    elif minutes < 60:
        return f"{minutes} min ago"
    elif hours < 24:
        return f"{hours} hr ago"
    elif days < 7:
        return f"{days} day{'s' if days != 1 else ''} ago"
    else:
        return value.strftime("%Y-%m-%d")