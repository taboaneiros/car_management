"""
Apps configuration for the sync module.
"""
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class SyncConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.sync"
    verbose_name = _("Offline Sync & PWA")

