"""
Custom forms for the RPG game
"""
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django import forms
from .models import Character
from .building_models import FlagColor

BASIC_COLOR_NAMES = ['red', 'blue', 'yellow', 'green']

class CombinedRegistrationForm(UserCreationForm):
    """Single-step registration + character creation form"""
    character_name = forms.CharField(max_length=50, help_text="Your character's display name", label="Character Name")
    class_type = forms.ChoiceField(choices=Character.CLASS_CHOICES, widget=forms.RadioSelect, label="Class")
    flag_color = forms.ModelChoiceField(
        queryset=FlagColor.objects.none(),
        widget=forms.RadioSelect,
        empty_label=None,
        label="Flag Color (basic colors)"
    )

    class Meta:
        model = User
        fields = ("username", "password1", "password2", "character_name", "class_type", "flag_color")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ensure basic flag colors exist so the form always has options
        defaults = {
            'red':    {'hex_color': '#FF0000', 'display_name': 'Red',    'is_premium': False, 'is_active': True},
            'blue':   {'hex_color': '#0000FF', 'display_name': 'Blue',   'is_premium': False, 'is_active': True},
            'yellow': {'hex_color': '#FFFF00', 'display_name': 'Yellow', 'is_premium': False, 'is_active': True},
            'green':  {'hex_color': '#00FF00', 'display_name': 'Green',  'is_premium': False, 'is_active': True},
        }
        need_seed = not FlagColor.objects.filter(is_active=True, is_premium=False, name__in=BASIC_COLOR_NAMES).exists()
        if need_seed:
            for name, attrs in defaults.items():
                FlagColor.objects.get_or_create(name=name, defaults=attrs)
        # Limit flag colors to active, non-premium basics
        qs = FlagColor.objects.filter(is_active=True, is_premium=False, name__in=BASIC_COLOR_NAMES).order_by('display_name')
        self.fields['flag_color'].queryset = qs
        # Show hex in label
        self.fields['flag_color'].label_from_instance = lambda obj: f"{obj.display_name} ({obj.hex_color})"
        # Provide sensible defaults if not bound
        if not self.is_bound:
            # Default class selection
            self.fields['class_type'].initial = 'cyber_warrior'
            # Default flag color selection if any available
            first = qs.first()
            if first:
                self.fields['flag_color'].initial = first.pk
        # Style existing form fields
        for field_name in ['username', 'password1', 'password2']:
            self.fields[field_name].widget.attrs.update({
                'class': 'form-control',
                'style': 'background: rgba(30, 30, 40, 0.8); border: 2px solid #2d3748; border-radius: 8px; color: #ffffff; font-size: 1rem;'
            })
        self.fields['character_name'].widget.attrs.update({
            'id': 'character_name',
            'class': 'form-control',
            'maxlength': '50',
            'pattern': '[A-Za-z0-9_\-\s]+',
            'title': 'Letters, numbers, spaces, hyphens and underscores only',
            'style': 'background: rgba(30, 30, 40, 0.8); border: 2px solid #2d3748; border-radius: 8px; color: #ffffff; font-size: 1rem;'
        })

    def clean_character_name(self):
        name = (self.cleaned_data.get('character_name') or '').strip()
        if not name:
            raise forms.ValidationError("Character name is required")
        # Do not enforce uniqueness here; the view will auto-generate a unique variant if needed
        return name

# Legacy form kept for backward-compat in legacy URLs
class CustomUserCreationForm(UserCreationForm):
    """Custom registration form (legacy)"""
    
    class Meta:
        model = User
        fields = ("username", "password1", "password2")

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


class CharacterCreationForm(forms.Form):
    """Character creation form used after account registration."""
    character_name = forms.CharField(max_length=50, label="Character Name")
    class_type = forms.ChoiceField(choices=Character.CLASS_CHOICES, widget=forms.RadioSelect, label="Class")
    flag_color = forms.ModelChoiceField(
        queryset=FlagColor.objects.none(),
        widget=forms.RadioSelect,
        empty_label=None,
        label="Flag Color"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ensure basic flag colors exist so the form always has options
        defaults = {
            'red':    {'hex_color': '#FF0000', 'display_name': 'Red',    'is_premium': False, 'is_active': True},
            'blue':   {'hex_color': '#0000FF', 'display_name': 'Blue',   'is_premium': False, 'is_active': True},
            'yellow': {'hex_color': '#FFFF00', 'display_name': 'Yellow', 'is_premium': False, 'is_active': True},
            'green':  {'hex_color': '#00FF00', 'display_name': 'Green',  'is_premium': False, 'is_active': True},
        }
        need_seed = not FlagColor.objects.filter(is_active=True, is_premium=False, name__in=BASIC_COLOR_NAMES).exists()
        if need_seed:
            for name, attrs in defaults.items():
                FlagColor.objects.get_or_create(name=name, defaults=attrs)
        # Limit flag colors to active, non-premium basics
        qs = FlagColor.objects.filter(is_active=True, is_premium=False, name__in=BASIC_COLOR_NAMES).order_by('display_name')
        self.fields['flag_color'].queryset = qs
        # Show hex in label
        self.fields['flag_color'].label_from_instance = lambda obj: f"{obj.display_name} ({obj.hex_color})"
        # Sensible defaults
        if not self.is_bound:
            self.fields['class_type'].initial = 'cyber_warrior'
            first = qs.first()
            if first:
                self.fields['flag_color'].initial = first.pk
        # Style fields and set attributes
        self.fields['character_name'].widget.attrs.update({
            'id': 'character_name',
            'class': 'form-control',
            'maxlength': '50',
            'pattern': '[A-Za-z0-9_\-\s]+' ,
            'title': 'Letters, numbers, spaces, hyphens and underscores only',
            'style': 'background: rgba(30, 30, 40, 0.8); border: 2px solid #2d3748; border-radius: 8px; color: #ffffff; font-size: 1rem;'
        })

    def clean_character_name(self):
        name = (self.cleaned_data.get('character_name') or '').strip()
        if not name:
            raise forms.ValidationError("Character name is required")
        if Character.objects.filter(name=name).exists():
            raise forms.ValidationError("Character name is already taken")
        return name
