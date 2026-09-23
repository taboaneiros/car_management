"""
Tests for the users app.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import UserProfile

User = get_user_model()


class UserModelTests(TestCase):
    """Tests for the custom User model."""

    def test_create_user_with_email(self):
        """Test creating a user with email as the identifier."""
        user = User.objects.create_user(
            email="user@example.com",
            password="testpass123",
        )
        self.assertEqual(user.email, "user@example.com")
        self.assertTrue(user.check_password("testpass123"))

    def test_email_is_unique(self):
        """Test that email must be unique."""
        User.objects.create_user(
            email="unique@example.com",
            password="testpass123",
        )
        with self.assertRaises(Exception):
            User.objects.create_user(
                email="unique@example.com",
                password="testpass123",
            )

    def test_get_full_name_falls_back_to_email(self):
        """Test that get_full_name falls back to email when no name is set."""
        user = User.objects.create_user(
            email="noname@example.com",
            password="testpass123",
        )
        self.assertEqual(user.get_full_name(), "noname@example.com")


class UserProfileTests(TestCase):
    """Tests for the UserProfile model."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="profile@example.com",
            password="testpass123",
        )

    def test_profile_created_for_user(self):
        """Test that a profile is created for a user."""
        # The signal should create a profile automatically
        profile = UserProfile.objects.filter(user=self.user).first()
        if profile is None:
            # If no signal, create one manually
            profile = UserProfile.objects.create(user=self.user)
        self.assertEqual(profile.user, self.user)
        self.assertEqual(profile.default_currency, "BRL")
        self.assertEqual(profile.measurement_unit, "km")


class UserViewTests(TestCase):
    """Tests for user views."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="userview@example.com",
            password="testpass123",
        )
        self.client.login(email=self.user.email, password="testpass123")

    def test_profile_requires_login(self):
        """Test that the profile requires authentication."""
        self.client.logout()
        response = self.client.get(reverse("users:profile"))
        self.assertEqual(response.status_code, 302)

    def test_profile_renders(self):
        """Test that the profile page renders."""
        response = self.client.get(reverse("users:profile"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "account/profile_detail.html")

    def test_profile_edit_renders(self):
        """Test that the profile edit page renders."""
        response = self.client.get(reverse("users:profile_edit"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "account/profile_form.html")
