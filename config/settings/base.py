"""
Base settings for car_management project.
All settings common to all environments should be defined here.
"""
from pathlib import Path

import environ
from django.utils.translation import gettext_lazy as _

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Initialize django-environ
env = environ.Env(
    DEBUG=(bool, False),
    EMAIL_USE_TLS=(bool, True),
    EMAIL_PORT=(int, 587),
)

# Read .env file
environ.Env.read_env(BASE_DIR / ".env")

# =============================================================================
# CORE SETTINGS
# =============================================================================

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["*"])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=["http://localhost:8000"])

# =============================================================================
# APPLICATION DEFINITION
# =============================================================================

INSTALLED_APPS = [
    # Django contrib
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party apps
    "allauth",
    "allauth.account",
    "allauth.mfa",
    "crispy_forms",
    "crispy_bootstrap5",
    "django_htmx",
    "rest_framework",
    # Local apps
    "apps.users",
    "apps.vehicles",
    "apps.fuel",
    "apps.expenses",
    "apps.maintenance",
    "apps.reminders",
    "apps.trips",
    "apps.checklists",
    "apps.reports",
    "apps.dashboard",
    "apps.imports",
    "apps.sync",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Allauth middleware
    "allauth.account.middleware.AccountMiddleware",
    # HTMX middleware
    "django_htmx.middleware.HtmxMiddleware",
]

ROOT_URLCONF = "config.urls"

# =============================================================================
# TEMPLATES
# =============================================================================

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# =============================================================================
# DATABASE
# =============================================================================

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# =============================================================================
# AUTHENTICATION
# =============================================================================

# Custom User Model
AUTH_USER_MODEL = "users.User"

# Django Allauth Configuration (updated for django-allauth >= 0.60)
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_LOGOUT_ON_GET = True
ACCOUNT_SESSION_REMEMBER = True

# Redirect URLs
LOGIN_REDIRECT_URL = "dashboard:home"
LOGOUT_REDIRECT_URL = "account_login"
LOGIN_URL = "account_login"

# Allauth adapter
ACCOUNT_ADAPTER = "apps.users.adapters.CustomAccountAdapter"

# =============================================================================
# PASSWORD VALIDATION
# =============================================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": 8,
        },
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# =============================================================================
# INTERNATIONALIZATION
# =============================================================================

LANGUAGE_CODE = env("LANGUAGE_CODE", default="pt-br")
TIME_ZONE = env("TIME_ZONE", default="America/Sao_Paulo")
USE_I18N = True
USE_TZ = True

LANGUAGES = [
    ("pt-br", _("Português (Brasil)")),
    ("en", _("English")),
    ("es", _("Español")),
]

LOCALE_PATHS = [
    BASE_DIR / "locale",
]

# =============================================================================
# STATIC AND MEDIA FILES
# =============================================================================

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# =============================================================================
# CRISPY FORMS
# =============================================================================

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# =============================================================================
# DEFAULT AUTO FIELD
# =============================================================================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# =============================================================================
# EMAIL CONFIGURATION
# =============================================================================

EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", default="smtp.example.com")
EMAIL_PORT = env("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env("EMAIL_USE_TLS", default=True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@example.com")

# =============================================================================
# FILE UPLOAD SETTINGS
# =============================================================================

# Maximum file size: 10MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

# Allowed file extensions for attachments
ALLOWED_ATTACHMENT_EXTENSIONS = ["jpg", "jpeg", "png", "webp", "pdf"]

# =============================================================================
# APP-SPECIFIC SETTINGS
# =============================================================================

# Pagination
PAGINATION_PAGE_SIZE = 20

# Dashboard settings
DASHBOARD_DEFAULT_DAYS = 30

# Reminder settings
REMINDER_DEFAULT_DAYS_BEFORE = 15
REMINDER_DEFAULT_KM_BEFORE = 500