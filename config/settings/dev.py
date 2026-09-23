"""
Development settings for car_management project.
"""
from .base import *

# =============================================================================
# DEBUG SETTINGS
# =============================================================================

DEBUG = True
ALLOWED_HOSTS = ["*"]

# =============================================================================
# EMAIL SETTINGS (Console backend for development)
# =============================================================================

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# =============================================================================
# ALLAUTH SETTINGS (Skip email verification in development)
# =============================================================================

ACCOUNT_EMAIL_VERIFICATION = "optional"  # Skip email verification in dev

# =============================================================================
# LOGGING
# =============================================================================

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.db.backends": {
            "handlers": ["console"],
            "level": "DEBUG",  # Show SQL queries in dev
            "propagate": False,
        },
    },
}

# =============================================================================
# STATIC FILES (Use django.contrib.staticfiles for development)
# =============================================================================

STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"