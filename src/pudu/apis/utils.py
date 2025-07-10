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