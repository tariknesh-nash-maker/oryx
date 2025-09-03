
from datetime import datetime, timedelta, timezone

def generate_digest(countries, hours=24, verified_only=True):
    """Fallback digest builder.
    Replace with your real logic or ensure `oryx_core.digest.generate_digest` is importable.
    Returns a Markdown string.
    """
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    header = f"Country updates (past {hours}h)\n\n"
    body_lines = []
    for c in countries:
        body_lines.append(f"*{c}*\n• (placeholder) Verified governance item A — source\n• (placeholder) Verified governance item B — source\n")
    return header + "\n".join(body_lines)
