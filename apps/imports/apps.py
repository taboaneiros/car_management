"""
App configuration for the imports app.
"""
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ImportsConfig(AppConfig):
    """Configuration for the imports app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.imports"
    verbose_name = _("Imports")
