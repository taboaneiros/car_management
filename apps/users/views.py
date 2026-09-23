"""
Views for the users app.
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic import DeleteView, DetailView, UpdateView

from .forms import AccountDeleteForm, ProfileUpdateForm
from .models import User, UserProfile


class ProfileDetailView(LoginRequiredMixin, DetailView):
    """
    View for displaying user profile.
    """

    model = UserProfile
    template_name = "account/profile_detail.html"
    context_object_name = "profile"

    def get_object(self, queryset=None):
        """Return the current user's profile, creating it if it doesn't exist."""
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        return profile


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    """
    View for updating user profile.
    """

    model = UserProfile
    form_class = ProfileUpdateForm
    template_name = "account/profile_form.html"
    success_url = reverse_lazy("users:profile")

    def get_object(self, queryset=None):
        """Return the current user's profile, creating it if it doesn't exist."""
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        return profile

    def form_valid(self, form):
        """Handle successful form submission."""
        messages.success(self.request, "Perfil atualizado com sucesso.")
        return super().form_valid(form)


class AccountDeleteView(LoginRequiredMixin, DeleteView):
    """
    View for deleting user account.
    Requires confirmation by typing the email address.
    """

    model = User
    template_name = "account/account_confirm_delete.html"
    success_url = reverse_lazy("account_login")

    def get_object(self, queryset=None):
        """Return the current user."""
        return self.request.user

    def get_context_data(self, **kwargs):
        """Add the deletion form to the context."""
        context = super().get_context_data(**kwargs)
        context["form"] = AccountDeleteForm(user=self.request.user)
        return context

    def post(self, request, *args, **kwargs):
        """Handle POST request for account deletion."""
        form = AccountDeleteForm(request.POST, user=request.user)
        if form.is_valid():
            # Delete the user account
            user = request.user
            user.delete()
            messages.success(
                request,
                "Sua conta foi excluída permanentemente. Até logo!",
            )
            return redirect(self.success_url)
        else:
            # Form is invalid, re-render with errors
            return render(
                request,
                self.template_name,
                {"object": request.user, "form": form},
            )