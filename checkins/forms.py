from __future__ import annotations

# imports
from django import forms
from .models import CheckIn, Habit, HRVReading, HabitAnchor


# define a model-based form for creating or editing check-ins
class CheckInForm(forms.ModelForm):
    class Meta:
        # bind the form to the CheckIn model
        model = CheckIn

        # specify which fields should appear in the form
        fields = ["status", "mood", "note", "tags", "hrv_rmssd"]

        # define form widgets for better input control and layout
        widgets = {
            "status": forms.Select(),  # dropdown for status choices
            "mood": forms.NumberInput(attrs={"min": 1, "max": 5}),  # numeric mood 1–5
            "note": forms.Textarea(attrs={"rows": 3}),  # multiline input for notes
        }

    # validate that mood value (if provided) is within valid range
    def clean_mood(self):
        m = self.cleaned_data.get("mood")  # extract mood value
        if m is not None and not (1 <= m <= 5):  # enforce valid range
            raise forms.ValidationError(
                "Mood must be between 1 and 5."
            )  # raise error if invalid
        return m  # return cleaned value

    # validate HRV field for positive numeric input
    def clean_hrv_rmssd(self):
        v = self.cleaned_data.get("hrv_rmssd")  # extract HRV value
        if v is not None and v <= 0:  # ensure HRV > 0
            raise forms.ValidationError(
                "HRV must be positive."
            )  # raise error if invalid
        return v  # return cleaned value


# define HabitForm for creating or editing user-defined habits
class HabitForm(forms.ModelForm):
    # lightweight validation for ease of use (Tiny Habits principle: lower friction)
    class Meta:
        # bind the form to the Habit model
        model = Habit

        # include key fields for creating a habit
        fields = [
            "name",
            "anchor_text",
            "prompt_type",
            "celebration_note",
        ]

        # customize form widgets with user-friendly placeholders
        widgets = {
            "anchor_text": forms.TextInput(
                attrs={
                    "placeholder": "After I start the kettle, I will fill my 12-oz water bottle."
                }
            ),
            "celebration_note": forms.TextInput(
                attrs={"placeholder": "Nice! / Fist bump / Small win 🔥"}
            ),
        }

    # gently process and sanitize the name field without blocking user input
    def clean_name(self):
        name = self.cleaned_data["name"].strip()  # trim whitespace
        # no strict validation — any hints handled in the template for flexibility
        return name


# Form to allow users to manually log HRV (heart rate variability) metrics
class HRVReadingForm(forms.ModelForm):

    class Meta:
        # bind to HRVReading model
        model = HRVReading

        # define the fields exposed in the form
        fields = ["rmssd_ms", "sdnn_ms", "resting_hr", "notes"]


# Form for creating and editing Tiny Habits recipes following
class HabitAnchorForm(forms.ModelForm):

    class Meta:
        # bind to HabitAnchor model
        model = HabitAnchor

        # expose all relevant recipe fields
        fields = ["anchor_action", "tiny_behavior", "celebration", "is_active"]

        # customize widget placeholders for user clarity
        widgets = {
            "anchor_action": forms.TextInput(
                attrs={"placeholder": "after I start my laptop in the morning"}
            ),
            "tiny_behavior": forms.TextInput(
                attrs={"placeholder": "I will open the HabitCoach dashboard"}
            ),
            "celebration": forms.TextInput(
                attrs={"placeholder": "I will say 'nice' to myself"}
            ),
        }
