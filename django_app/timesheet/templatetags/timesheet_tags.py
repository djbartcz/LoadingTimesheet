from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Get item from dictionary by key"""
    if dictionary is None:
        return None
    return dictionary.get(key)

@register.filter
def mod(value, arg):
    """Modulo filter"""
    try:
        return int(value) % int(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def format_duration_seconds(seconds):
    """Format duration in seconds to readable format"""
    if not seconds:
        return "0s"
    try:
        seconds = int(seconds)
        if seconds < 60:
            return f"{seconds}s"
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        if remaining_seconds == 0:
            return f"{minutes}min"
        return f"{minutes}min {remaining_seconds}s"
    except (ValueError, TypeError):
        return "0s"

