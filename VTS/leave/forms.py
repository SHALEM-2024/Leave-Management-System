from django import forms
from .models import Request

# For HR_clerk
from django import forms
from .models import DateExclusionRestriction, AdjacentDayRestriction, ConsecutiveDayRestriction, CoworkerRestriction, DayOfWeekRestriction, PeriodLimitRestriction

# Form for Employee leave request
class RequestForm(forms.ModelForm):
    class Meta:
        model = Request
        fields = ['category', 'title', 'description', 'start_date', 'end_date', 'hours_per_day']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }

# Form for HR_clerk
RESTRICTION_TYPE_CHOICES = [
    ('DateExclusionRestriction', 'Date Exclusion Restriction'),
    ('AdjacentDayRestriction', 'Adjacent Day Restriction'),
    ('ConsecutiveDayRestriction', 'Consecutive Day Restriction'),
    ('CoworkerRestriction', 'Coworker Restriction'),
    ('DayOfWeekRestriction', 'Day of Week Restriction'),
    ('PeriodLimitRestriction', 'Period Limit Restriction'),
]

class RestrictionForm(forms.Form):
    restriction_type = forms.ChoiceField(choices=RESTRICTION_TYPE_CHOICES, label="Restriction Type")
    name = forms.CharField(max_length=255)
    description = forms.CharField(widget=forms.Textarea, required=False)
    # Optional: allow selecting Category and Location to which the restriction applies.
    category = forms.CharField(max_length=100, required=False, help_text="Enter category ID or leave blank if not applicable")
    location = forms.CharField(max_length=100, required=False, help_text="Enter location ID or leave blank if not applicable")
    # For simplicity, we capture parameters as a JSON string.
    parameters = forms.CharField(widget=forms.Textarea(attrs={'rows':4, 'cols':50}), help_text="Enter parameters as a JSON object", required=False)
