"""
Custom adapter for django-allauth.
Customizes the authentication behavior to use email as the primary identifier.
"""
from allauth.account.adapter import DefaultAccountAdapter
from django.forms import ValidationError


class CustomAccountAdapter(DefaultAccountAdapter):
    """
    Custom adapter for django-allauth.
    Handles email-based authentication and user creation.
    """

    def authentication_allowed(self, request, email):
        """Check if authentication is allowed for this email."""
        return True

    def clean_email(self, email):
        """Validate and clean the email address."""
        return super().clean_email(email)

    def get_user_username(self, user):
        """Return the email as the username."""
        return user.email

    def generate_unique_username(self, txts, regex=None):
        """
        Generate a unique username.
        Since we use email for authentication, we generate a random username.
        """
        import uuid
        return str(uuid.uuid4())[:30]

    def save_user(self, request, user, form, commit=True):
        """
        Save a new user during signup.
        Ensures the username is set to a unique value.
        """
        # Generate a unique username if not set
        if not user.username:
            user.username = self.generate_unique_username([user.email])
        
        # Save the user using the parent method
        user = super().save_user(request, user, form, commit=commit)
        
        return user

    def populate_username(self, request, user):
        """
        Populate the username field.
        Since we use email for authentication, we set a random username.
        """
        if not user.username:
            user.username = self.generate_unique_username([user.email])