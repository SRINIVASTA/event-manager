class EventManagerException(Exception):
    """Base exception for the event manager system."""
    pass

class ConfigurationError(EventManagerException):
    """Raised when Streamlit Secrets are missing or invalid."""
    pass

class DatabaseError(EventManagerException):
    """Raised when Google Sheets mutations fail."""
    pass

class CommunicationError(EventManagerException):
    """Raised when SMTP/IMAP protocol operations fail."""
    pass
