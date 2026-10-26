"""Display-only formatting; stored values and identifiers remain unchanged."""
from datetime import datetime, timezone


def format_timestamp(value):
    """Format an aware ISO timestamp as a concise, explicitly UTC date.

    Unknown and timezone-free values are shown verbatim rather than assigning
    an undocumented timezone or preventing a history screen from opening.
    """
    if not isinstance(value, str):
        return '' if value is None else str(value)
    try:
        stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if stamp.tzinfo is None or stamp.utcoffset() is None:
            return value
        stamp = stamp.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        return value
    month = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
             'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')[stamp.month - 1]
    return f'{stamp.day:02d} {month} {stamp.year} · {stamp:%H:%M} UTC'
