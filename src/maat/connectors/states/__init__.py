from .base import StateSource
from .indiana import IndianaSource

__all__ = ['StateSource', 'IndianaSource', 'SOURCES', 'get_state_source']

SOURCES = {'IN': IndianaSource}


def get_state_source(state_code: str) -> StateSource:
    """Return the StateSource for a two-letter state code (case-insensitive)."""
    try:
        return SOURCES[state_code.upper()]()
    except KeyError:
        raise ValueError(f'no state source for {state_code!r}; have: {sorted(SOURCES)}')
