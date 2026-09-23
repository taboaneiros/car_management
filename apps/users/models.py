"""
User models for car_management project.
Custom User model with email as the primary identifier.
"""
from django.contrib.auth.models import AbstractUser, UserManager
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class CustomUserManager(UserManager):
    """
    Custom manager that makes the username optional.

    The default Django UserManager requires a username positional argument.
    Since this project uses email as the primary identifier, username is
    optional and can be omitted when creating users.
    """

    def _create_user(self, username, email, password, **extra_fields):
        """Create and save a user with the given email and password."""
        if not email:
            raise ValueError("The given email must be set")
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular user with the given email and password."""
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(None, email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a superuser with the given email and password."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(None, email, password, **extra_fields)


class User(AbstractUser):
    """
    Custom User model that uses email as the primary identifier.
    Username is kept for Django compatibility but not used for authentication.
    """

    # Use the custom manager that makes username optional
    objects = CustomUserManager()


    # Make username optional (Django requires it by default)
    username = models.CharField(
        _("username"),
        max_length=150,
        unique=True,
        blank=True,
        null=True,
        help_text=_(
            "Optional. 150 characters or fewer. Letters, digits and @/./+/-/_ only."
        ),
    )
    # Email is required and unique
    email = models.EmailField(_("email address"), unique=True)

    # Use email as the username field for authentication
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []  # Email is already required

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        db_table = "users_user"

    def __str__(self):
        return self.email

    def get_full_name(self):
        """Return the full name or email if not set."""
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name if full_name else self.email


class UserProfile(models.Model):
    """
    Extended profile information for users.
    Contains preferences and additional user data.
    """

    class MeasurementUnit(models.TextChoices):
        KILOMETERS = "km", _("Kilometers")
        MILES = "mi", _("Miles")

    class Currency(models.TextChoices):
        BRL = "BRL", _("Brazilian Real (R$)")
        USD = "USD", _("US Dollar ($)")
        EUR = "EUR", _("Euro (€)")

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name=_("user"),
    )
    full_name = models.CharField(_("full name"), max_length=255, blank=True)
    default_currency = models.CharField(
        _("default currency"),
        max_length=3,
        choices=Currency.choices,
        default=Currency.BRL,
    )
    language = models.CharField(_("language"), max_length=10, default="pt-br")
    timezone = models.CharField(_("timezone"), max_length=50, default="America/Sao_Paulo")
    measurement_unit = models.CharField(
        _("measurement unit"),
        max_length=2,
        choices=MeasurementUnit.choices,
        default=MeasurementUnit.KILOMETERS,
    )
    country_code = models.CharField(_("country code"), max_length=2, default="BR")
    avatar = models.ImageField(
        _("avatar"),
        upload_to="avatars/",
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("user profile")
        verbose_name_plural = _("user profiles")
        db_table = "users_profile"

    def __str__(self):
        return f"Profile of {self.user.email}"

    def get_display_name(self):
        """Return the name to display for the user."""
        if self.full_name:
            return self.full_name
        if self.user.first_name:
            return self.user.first_name
        return self.user.email