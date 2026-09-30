from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import UserPreferences

User = get_user_model()


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(
            attrs={
                "autocomplete": "email",
                "autofocus": True,
                "placeholder": "you@example.com",
            }
        ),
    )
    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "current-password",
                "placeholder": "Password",
            }
        ),
    )


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(
            attrs={
                "autocomplete": "email",
                "autofocus": True,
                "placeholder": "you@example.com",
            }
        ),
    )
    password1 = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "new-password",
                "placeholder": "Password",
            }
        ),
    )
    password2 = forms.CharField(
        label="Confirm password",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "new-password",
                "placeholder": "Confirm password",
            }
        ),
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("email",)

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "An account with this email address already exists."
            )
        return email



class UserPreferencesForm(forms.ModelForm):
    kelly_fraction = forms.ChoiceField(
        choices=[
            ("1.00", "Full"),
            ("0.50", "Half"),
            ("0.25", "Quarter"),
        ],
        widget=forms.Select(
            attrs={"aria-label": "Preferred Kelly fraction"}
        ),
    )

    class Meta:
        model = UserPreferences
        fields = ("timezone", "bankroll", "kelly_fraction")
        widgets = {
            "timezone": forms.Select(attrs={"aria-label": "Preferred timezone"}),
            "bankroll": forms.NumberInput(
                attrs={
                    "min": "0",
                    "step": "0.01",
                    "placeholder": "10000",
                    "autocomplete": "off",
                    "inputmode": "decimal",
                }
            ),
        }
