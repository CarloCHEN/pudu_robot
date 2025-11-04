def convert_technical_string(text):
    """
    Convert technical strings to human-readable format.
    Examples:
        OdomSlip -> Odom Slip
        U_PHASE_HARDWARE_OVER_CURRENT -> U Phase Hardware Over Current
        LaserLocateLose -> Laser Locate Lose
    """
    if not text:
        return text

    # Handle underscore-separated strings (like U_PHASE_HARDWARE_OVER_CURRENT)
    if '_' in text:
        words = text.split('_')
        # Convert each word to title case
        formatted_words = [word.capitalize() for word in words]
        return ' '.join(formatted_words)

    # Handle camelCase strings (like OdomSlip, LaserLocateLose)
    else:
        # Insert space before uppercase letters (except the first one)
        import re
        # This regex finds positions where a lowercase letter is followed by an uppercase letter
        spaced = re.sub('([a-z])([A-Z])', r'\1 \2', text)
        # Convert to title case
        return spaced.title()

def clean_map_name(map_name: str) -> str:
    """
    Remove the prefix up to and including the first two '#' characters
    from a map_name string. If fewer than two '#' are found,
    return the original string.
    """
    if not map_name:
        return None
    if '#' not in map_name:
        return map_name
    parts = map_name.split("#", 2)
    return parts[2] if len(parts) > 2 else map_name