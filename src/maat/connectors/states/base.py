from abc import ABC, abstractmethod


class StateSource(ABC):
    """Pluggable per-state source of forms, court rules, fees, and self-help links.

    Every URL listed by an implementation MUST have been verified with an
    actual HTTP request returning 200. Every fee amount MUST be verified
    from an official source; unverifiable fees use amount_cents=None and
    verified=False. Nothing is ever invented.
    """

    @abstractmethod
    def state_code(self) -> str:
        """Two-letter state code, e.g. 'IN'."""

    @abstractmethod
    def forms_index(self) -> list:
        """List of {'name', 'url', 'description'} — official court forms."""

    @abstractmethod
    def court_rules(self) -> list:
        """List of {'name', 'url'} — official rules of court."""

    @abstractmethod
    def fee_schedule(self) -> list:
        """List of {'court', 'filing_type', 'amount_cents' or None,
        'verified': bool, 'source_url': str, 'description': str}."""

    @abstractmethod
    def self_help_links(self) -> list:
        """List of {'name', 'url', 'description'} — self-help resources."""
