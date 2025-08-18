"""
Custom forms for the RPG game
"""
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .building_models import FlagColor


class CustomUserCreationForm(UserCreationForm):
    """Custom registration form with flag color selection"""
    flag_color = forms.ModelChoiceField(
        queryset=FlagColor.objects.filter(is_active=True, unlock_level__lte=1),
        empty_label="Choose your flag color",
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'style': 'background: rgba(30, 30, 40, 0.8); border: 2px solid #2d3748; border-radius: 8px; color: #ffffff; font-size: 1rem;'
        }),
        help_text="This will be the color of all flags you place in the game."
    )

    class Meta:
        model = User
        fields = ("username", "password1", "password2", "flag_color")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Style the form fields
        for field_name in ['username', 'password1', 'password2']:
            self.fields[field_name].widget.attrs.update({
                'class': 'form-control',
                'style': 'background: rgba(30, 30, 40, 0.8); border: 2px solid #2d3748; border-radius: 8px; color: #ffffff; font-size: 1rem;'
            })

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
        return user
