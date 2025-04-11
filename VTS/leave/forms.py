from django import forms
from .models import Request
from django.contrib.auth.forms import UserCreationForm
from .models import User

# For HR_clerk
from django import forms
from .models import DateExclusionRestriction, AdjacentDayRestriction, ConsecutiveDayRestriction, CoworkerRestriction, DayOfWeekRestriction, PeriodLimitRestriction, Category, Restriction, Location

# Form for Employee leave request

class RequestForm(forms.ModelForm):
    class Meta:
        model = Request
        fields = ['category', 'title', 'description', 'start_date', 'end_date', 'hours_per_day']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        # Pop the 'user' from kwargs and set it to the instance's employee field.
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.instance.employee = user  # Ensure employee is set even for new records.

    def clean(self):
        # Call the parent clean method.
        cleaned_data = super().clean()
        # Check that the employee is set. This should now always be the case.
        if not self.instance.employee:
            raise forms.ValidationError("Employee is not set. Please refresh the page.")
        # Validate that end_date is not before start_date.
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        """
        if start_date and end_date and end_date < start_date:
            self.add_error('end_date', 'End date cannot be before start date.')
        
        # Check for overlapping requests.
        overlapping_requests = Request.objects.filter(
            employee=self.instance.employee,
            start_date__lte=end_date,
            end_date__gte=start_date
        )
        
        if self.instance.pk:
            overlapping_requests = overlapping_requests.exclude(pk=self.instance.pk)
        if overlapping_requests.exists():
            raise forms.ValidationError("There is an existing leave request that overlaps with these dates. Please delete or modify the existing request first.")
        """
        return cleaned_data


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
    # For multiple selection:
    category = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all(),
        required=False,
        help_text="Select one or more categories to which this restriction applies"
    )
    location = forms.ModelMultipleChoiceField(
        queryset=Location.objects.all(),
        required=False,
        help_text="Select one or more locations to which this restriction applies"
    )
    parameters = forms.CharField(
        widget=forms.Textarea(attrs={'rows':4, 'cols':50}),
        help_text="Enter parameters as a JSON object",
        required=False
    )


class CustomUserCreationForm(UserCreationForm):
    # Optionally, you can include additional fields (e.g., role or location) if needed.
    # For now, we’ll use the default ones.
    
    class Meta:
        model = User
        # Include only the fields you want new users to supply.
        fields = ('username', 'email', 'role',)
        # You could also include additional fields such as first_name, last_name, etc.
