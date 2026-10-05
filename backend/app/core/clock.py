from datetime import date


def today() -> date:
    """Business 'today'. A dependency so tests and demos can pin the date."""
    return date.today()
