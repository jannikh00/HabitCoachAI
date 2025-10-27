# imports
from django import forms
from .models import CheckIn


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
