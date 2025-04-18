from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
import datetime
from django.core.exceptions import ValidationError


# ---------------------------
# Custom User Model (Employee)
# ---------------------------
class User(AbstractUser):
    ROLE_CHOICES = (
        ('employee', 'Employee'),
        ('manager', 'Manager'),
        ('hr_clerk', 'HR Clerk'),
        ('admin', 'System Admin'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='employee')
    # Each employee is associated with one Location.
    location = models.ForeignKey('Location', on_delete=models.SET_NULL, null=True, blank=True, related_name='employees')
    # Self-association to denote manager-subordinate relationships.
    managers = models.ManyToManyField('self', symmetrical=False, related_name='subordinates', blank=True)
    
    def __str__(self):
        return self.username

# ---------------------------
# Location Model
# ---------------------------
class Location(models.Model):
    name = models.CharField(max_length=255)
    address = models.TextField(blank=True, null=True)  # Optional address field.
    
    def __str__(self):
        return self.name

# ---------------------------
# Category Model (e.g., Vacation, Sick Leave)
# ---------------------------
class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return self.name

# ---------------------------
# Grant Model
# Represents the leave time available to an employee.
# ---------------------------
class Grant(models.Model):

    employee_category = models.CharField(max_length=20,choices=User.ROLE_CHOICES, default='employee',help_text="Select the employee category to which this grant applies.")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='grants')
    allocated_hours = models.IntegerField()  # Total hours available for this grant.
    expiration_date = models.DateField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.employee_category} - {self.category.name} Grant"


class UserLeaveBalance(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='leave_balances')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='user_leave_balances')
    allocated_hours = models.IntegerField(
        help_text="Total allocated leave hours for this category.",
        blank=True, null=True  # Allow blank initially; will be set in save()
    )
    remaining_hours = models.IntegerField(
        help_text="Remaining leave hours for this category.",
        blank=True, null=True  # Allow blank initially; will be set in save()
    )

    class Meta:
        unique_together = ('user', 'category')

    def save(self, *args, **kwargs):
        # When creating a new UserLeaveBalance, if the balance is not yet set,
        # look up the matching Grant based on the user's role and the category.
        if self.pk is None:
            try:
                grant = Grant.objects.get(employee_category=self.user.role, category=self.category)
            except Grant.DoesNotExist:
                raise ValueError("No grant exists for this user and category. Please contact HR.")
            # Set the allocated and remaining hours from the Grant.
            self.allocated_hours = grant.allocated_hours
            self.remaining_hours = grant.allocated_hours
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.category.name}: {self.remaining_hours}/{self.allocated_hours}"

# ---------------------------
# Request Model
# Represents a vacation time request.
# ---------------------------

class Request(models.Model):
    STATUS_CHOICES = [
        ('created', 'Created'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('withdrawn', 'Withdrawn'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]
    
    employee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='requests')
    #grant = models.ForeignKey(Grant, on_delete=models.CASCADE, related_name='requests')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='requests')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    hours_per_day = models.FloatField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='created')
    created_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(blank=True, null=True)
    
    def clean(self):
        # First, allow any built-in validations to run
        super().clean()
        
        # Ensure the end_date is not before the start_date
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError({'end_date': "End date cannot be before start date."})
        
        # Check for overlapping requests for the same employee.
        # An overlap occurs if: new.start_date <= existing.end_date AND new.end_date >= existing.start_date.
        overlapping_requests = Request.objects.filter(
            employee=self.employee,
            start_date__lte=self.end_date,
            end_date__gte=self.start_date
        )
        # When updating an existing request, exclude itself from the check.
        if self.pk:
            overlapping_requests = overlapping_requests.exclude(pk=self.pk)
        
        if overlapping_requests.exists():
            raise ValidationError("There is an existing leave request that overlaps with these dates. Please delete or modify the existing request first.")

        # Now, validate all applicable restrictions.
        errors = []
        # Define the list of concrete restriction classes.
        restriction_classes = [
            DateExclusionRestriction,
            AdjacentDayRestriction,
            ConsecutiveDayRestriction,
            CoworkerRestriction,
            DayOfWeekRestriction,
            PeriodLimitRestriction,
        ]
        # For each restriction class, get restrictions that apply.
        # Here we use a simple filter based on category.
        for RestrictionClass in restriction_classes:
            applicable_restrictions = RestrictionClass.objects.filter(category=self.category)
            for restr in applicable_restrictions:
                result = restr.validate(self)
                if not result.validated():
                    errors.extend(result.get_errors())
        if errors:
            # Raise a non-field error with all the collected messages.
            raise ValidationError({'__all__': errors})
        
    def save(self, *args, **kwargs):
        # Enforce validation before saving
        self.full_clean()
        super().save(*args, **kwargs)
        
    def __str__(self):
        username = self.employee.username if self.employee else "Unassigned"
        return f"{self.employee.username} Request: {self.title} ({self.status})"

# ---------------------------
# ValidationResult Helper Class
# Not a model; used to capture the outcome of a restriction validation.
# ---------------------------
class ValidationResult:
    def __init__(self):
        self.errors = []
    
    def add_error(self, message):
        self.errors.append(message)
    
    def validated(self):
        return len(self.errors) == 0
    
    def get_errors(self):
        return self.errors

# ---------------------------
# RestrictionParameterDescriptor Helper Class
# Encapsulates metadata about required parameters for a restriction.
# ---------------------------
class RestrictionParameterDescriptor:
    def __init__(self, name, description, data_type=str, default_value=None):
        self.name = name
        self.description = description
        self.data_type = data_type
        self.default_value = default_value
    
    def __repr__(self):
        return f"RestrictionParameterDescriptor(name={self.name}, type={self.data_type.__name__})"

# ---------------------------
# Abstract Restriction Class
# ---------------------------
class Restriction(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    # Restrictions can be applied broadly via Category and/or Location.
    category = models.ManyToManyField(Category, blank=True, related_name='%(class)s_restrictions')
    location = models.ManyToManyField(Location, blank=True, related_name='%(class)s_restrictions')
    # Store parameter values as key-value pairs (e.g., {"X": value, "Y": value})
    parameters = models.JSONField(default=dict, blank=True)
    
    class Meta:
        abstract = True
    
    def get_parameter(self, key):
        return self.parameters.get(key)
    
    def set_parameter(self, key, value):
        self.parameters[key] = value
        self.save()
    
    def validate(self, request_obj):
        """
        Abstract method; concrete subclasses must implement this.
        Should return a ValidationResult object.
        """
        raise NotImplementedError("Subclasses must implement validate()")

# ---------------------------
# Concrete Restriction Subclasses
# ---------------------------

class DateExclusionRestriction(Restriction):
    """
    Prevents requests on specified dates.
    Expects a parameter "excluded_dates": a list of ISO date strings.
    """
    def validate(self, request_obj):
        result = ValidationResult()
        excluded_dates = self.get_parameter("excluded_dates") or []
        try:
            excluded_dates = [datetime.datetime.strptime(d, "%Y-%m-%d").date() for d in excluded_dates]
        except Exception:
            result.add_error("Invalid date format in excluded_dates parameter.")
            return result
        
        current_date = request_obj.start_date
        while current_date <= request_obj.end_date:
            if current_date in excluded_dates:
                result.add_error(f"Date {current_date} is excluded.")
            current_date += datetime.timedelta(days=1)
        
        return result

class AdjacentDayRestriction(Restriction):
    """
    Ensures vacation time is not taken directly adjacent to specified holidays.
    Expects a parameter "holidays": a list of ISO date strings.
    """
    def validate(self, request_obj):
        result = ValidationResult()
        holidays = self.get_parameter("holidays") or []
        try:
            holidays = [datetime.datetime.strptime(d, "%Y-%m-%d").date() for d in holidays]
        except Exception:
            result.add_error("Invalid date format in holidays parameter.")
            return result
        
        for holiday in holidays:
            if request_obj.start_date == holiday - datetime.timedelta(days=1) or request_obj.end_date == holiday + datetime.timedelta(days=1):
                result.add_error(f"Request is adjacent to holiday on {holiday}.")
        return result

class ConsecutiveDayRestriction(Restriction):
    """
    Limits the number of consecutive days off.
    Expects a parameter "max_consecutive_days": an integer.
    """
    def validate(self, request_obj):
        result = ValidationResult()
        max_days = self.get_parameter("max_consecutive_days")
        if max_days is None:
            result.add_error("Parameter 'max_consecutive_days' not set.")
            return result
        total_days = (request_obj.end_date - request_obj.start_date).days + 1
        if total_days > max_days:
            result.add_error(f"Request exceeds maximum consecutive days ({max_days}).")
        return result

class CoworkerRestriction(Restriction):
    """
    Ensures that a minimum number of coworkers remain scheduled.
    Expects parameters:
      - "min_count": integer representing the minimum required number of coworkers.
    """
    def validate(self, request_obj):
        result = ValidationResult()
        min_count = self.get_parameter("min_count")
        if min_count is None:
            result.add_error("Parameter 'min_count' not set.")
            return result
        try:
            min_count = int(min_count)
        except ValueError:
            result.add_error("Parameter 'min_count' must be an integer.")
            return result

        # Helper function: For a given date, compute number of scheduled coworkers.
        def get_scheduled_coworker_count(employee, date):
            # Get all employees at the same location except the current employee.
            total_at_location = employee.location.employees.exclude(id=employee.id).count()
            # Find out how many are on leave on that specific date.
            # Consider Requests in statuses that represent active leave (e.g., 'submitted' and 'approved').
            on_leave = Request.objects.filter(
                employee__location=employee.location,
                start_date__lte=date,
                end_date__gte=date,
                status__in=['submitted', 'approved']
            ).values_list('employee', flat=True).distinct().count()
            # Scheduled coworkers are those who are at the location but not on leave.
            return total_at_location - on_leave

        current_date = request_obj.start_date
        while current_date <= request_obj.end_date:
            scheduled_count = get_scheduled_coworker_count(request_obj.employee, current_date)
            if scheduled_count < min_count:
                result.add_error(
                    f"On {current_date}, only {scheduled_count} coworkers are scheduled, which is less than the required minimum of {min_count}."
                )
            current_date += datetime.timedelta(days=1)
        return result

class DayOfWeekRestriction(Restriction):
    """
    Restricts requests to specified days of the week.
    Expects a parameter "allowed_days": a list of weekday numbers (0=Monday, 6=Sunday).
    """
    def validate(self, request_obj):
        result = ValidationResult()
        allowed_days = self.get_parameter("allowed_days")
        if allowed_days is None:
            result.add_error("Parameter 'allowed_days' not set.")
            return result
        
        current_date = request_obj.start_date
        while current_date <= request_obj.end_date:
            if current_date.weekday() not in allowed_days:
                result.add_error(f"Day {current_date} (weekday {current_date.weekday()}) is not allowed for leave.")
            current_date += datetime.timedelta(days=1)
        return result

class PeriodLimitRestriction(Restriction):
    """
    Limits total hours of leave in a given period (e.g., week or month).
    Expects parameters:
      - "max_hours": maximum allowed hours.
      - "period": string indicating the period ('week' or 'month').
    """
    def validate(self, request_obj):
        result = ValidationResult()
        max_hours = self.get_parameter("max_hours")
        period = self.get_parameter("period")
        if max_hours is None or period is None:
            result.add_error("Parameters 'max_hours' and/or 'period' not set.")
            return result
        
        # For demonstration, calculate total hours for the request.
        total_days = (request_obj.end_date - request_obj.start_date).days + 1
        total_hours = request_obj.hours_per_day * total_days
        if total_hours > max_hours:
            result.add_error(f"Total requested hours ({total_hours}) exceed the limit of {max_hours} for the {period}.")
        return result