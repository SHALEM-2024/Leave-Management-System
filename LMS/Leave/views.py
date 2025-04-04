import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Request, User
from .forms import RequestForm

#for Manager functionality
from django.http import HttpResponse
from django.core.mail import send_mail

#for HR_clerk functionality
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from .models import (
    DateExclusionRestriction,
    AdjacentDayRestriction,
    ConsecutiveDayRestriction,
    CoworkerRestriction,
    DayOfWeekRestriction,
    PeriodLimitRestriction,
)

from .forms import RestrictionForm


@login_required
def home(request):
    user = request.user
    today = timezone.now().date()
    six_months_ago = today - datetime.timedelta(days=180)
    eighteen_months_future = today + datetime.timedelta(days=18*30)  # approximate

    # Retrieve employee's own requests in the defined time range.
    my_requests = Request.objects.filter(
        employee=user,
        start_date__gte=six_months_ago,
        end_date__lte=eighteen_months_future
    )

    context = {
        'user': user,
        'current_date': today,
        'message': "Welcome to the Vacation Tracking System!",
        'my_requests': my_requests,
    }
    
    # PendingForApprovalByYourManager: requests that the user has submitted (awaiting approval)
    pending_for_manager = Request.objects.filter(employee=user, status='submitted')
    context['pending_for_manager'] = pending_for_manager

    # For managers: display subordinate requests pending their approval.
    if user.role == 'manager':
        subordinate_ids = user.subordinates.values_list('id', flat=True)
        pending_for_you = Request.objects.filter(employee__id__in=subordinate_ids, status='submitted')
        context['pending_for_you'] = pending_for_you

    return render(request, 'leave/home.html', context)

@login_required
def request_editor(request):
    """
    Displays a form for creating a new vacation request.
    """
    if request.method == 'POST':
        form = RequestForm(request.POST)
        if form.is_valid():
            new_request = form.save(commit=False)
            new_request.employee = request.user
            new_request.status = 'submitted'
            new_request.submitted_at = timezone.now()
            new_request.save()
            # (Optional: Trigger email notification to the manager(s) here)
            return redirect('home')
    else:
        form = RequestForm()
    
    return render(request, 'leave/request_editor.html', {'form': form})

@login_required
def withdraw_request(request, request_id):
    """
    Allows an employee to withdraw a pending vacation request.
    """
    req_obj = get_object_or_404(Request, id=request_id, employee=request.user, status='submitted')
    if request.method == 'POST':
        req_obj.status = 'withdrawn'
        req_obj.save()
        # (Optional: Trigger email notification to the manager here)
        return redirect('home')
    
    return render(request, 'leave/withdraw_confirmation.html', {'request_obj': req_obj})

@login_required
def cancel_request(request, request_id):
    """
    Allows an employee to cancel an approved vacation request.
    For future requests, a simple confirmation is required.
    For recent past requests, an explanation must be provided.
    """
    req_obj = get_object_or_404(Request, id=request_id, employee=request.user, status='approved')
    if request.method == 'POST':
        # For recent past requests, an explanation might be required.
        explanation = request.POST.get('explanation', '')
        # (Optional: Save the explanation or log it as needed)
        req_obj.status = 'cancelled'
        req_obj.save()
        # (Optional: Reallocate time allowances and send notification email)
        return redirect('home')
    
    return render(request, 'leave/cancel_confirmation.html', {'request_obj': req_obj})

@login_required
def edit_request(request, request_id):
    """
    Allows an employee to edit a pending vacation request.
    The employee may update details like the title, description, or dates.
    """
    req_obj = get_object_or_404(Request, id=request_id, employee=request.user, status='submitted')
    if request.method == 'POST':
        form = RequestForm(request.POST, instance=req_obj)
        if form.is_valid():
            form.save()
            return redirect('home')
    else:
        form = RequestForm(instance=req_obj)
    
    return render(request, 'leave/edit_request.html', {'form': form, 'request_obj': req_obj})



# Manager functionality

@login_required
def approve_request(request, request_id):
    # Only allow managers to perform this action.
    if request.user.role != 'manager':
        return HttpResponse("Permission denied", status=403)
    
    req_obj = get_object_or_404(Request, id=request_id)
    
    # Ensure the request is still pending approval.
    if req_obj.status != 'submitted':
        return redirect('home')
    
    if request.method == 'POST':
        req_obj.status = 'approved'
        req_obj.save()
        
        # Optionally send an email notification to the employee.
        send_mail(
            subject="Your vacation request has been approved",
            message=f"Hello {req_obj.employee.username}, your vacation request '{req_obj.title}' has been approved.",
            from_email="no-reply@yourcompany.com",
            recipient_list=[req_obj.employee.email],
            fail_silently=True,
        )
        return redirect('home')
    
    return render(request, 'leave/approve_confirmation.html', {'request_obj': req_obj})

@login_required
def reject_request(request, request_id):
    # Only allow managers to perform this action.
    if request.user.role != 'manager':
        return HttpResponse("Permission denied", status=403)
    
    req_obj = get_object_or_404(Request, id=request_id)
    
    # Ensure the request is still pending approval.
    if req_obj.status != 'submitted':
        return redirect('home')
    
    if request.method == 'POST':
        explanation = request.POST.get('explanation', '').strip()
        if not explanation:
            error_message = "Please provide an explanation for rejection."
            return render(request, 'leave/reject_request.html', {'request_obj': req_obj, 'error': error_message})
        
        req_obj.status = 'rejected'
        req_obj.save()
        
        # Optionally send an email notification to the employee.
        send_mail(
            subject="Your vacation request has been rejected",
            message=f"Hello {req_obj.employee.username}, your vacation request '{req_obj.title}' has been rejected.\nExplanation: {explanation}",
            from_email="no-reply@yourcompany.com",
            recipient_list=[req_obj.employee.email],
            fail_silently=True,
        )
        return redirect('home')
    
    return render(request, 'leave/reject_request.html', {'request_obj': req_obj})


# HR_clerk functionality

import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from .models import (
    DateExclusionRestriction,
    AdjacentDayRestriction,
    ConsecutiveDayRestriction,
    CoworkerRestriction,
    DayOfWeekRestriction,
    PeriodLimitRestriction,
)

from .forms import RestrictionForm

@login_required
def hr_restriction_list(request):
    if request.user.role != 'hr_clerk':
        return HttpResponse("Permission denied", status=403)
    
    # Combine restrictions from all concrete subclasses
    restrictions = []
    restrictions += list(DateExclusionRestriction.objects.all())
    restrictions += list(AdjacentDayRestriction.objects.all())
    restrictions += list(ConsecutiveDayRestriction.objects.all())
    restrictions += list(CoworkerRestriction.objects.all())
    restrictions += list(DayOfWeekRestriction.objects.all())
    restrictions += list(PeriodLimitRestriction.objects.all())
    
    context = {'restrictions': restrictions}
    return render(request, 'leave/hr_restriction_list.html', context)

@login_required
def hr_restriction_create(request):
    if request.user.role != 'hr_clerk':
        return HttpResponse("Permission denied", status=403)
    
    if request.method == 'POST':
        form = RestrictionForm(request.POST)
        if form.is_valid():
            rtype = form.cleaned_data['restriction_type']
            name = form.cleaned_data['name']
            description = form.cleaned_data['description']
            # For simplicity, we'll assume category and location are provided as IDs (or leave blank)
            category = form.cleaned_data['category'] or None
            location = form.cleaned_data['location'] or None
            parameters_str = form.cleaned_data['parameters']
            try:
                parameters = json.loads(parameters_str) if parameters_str else {}
            except json.JSONDecodeError:
                form.add_error('parameters', "Invalid JSON format.")
                return render(request, 'leave/hr_restriction_form.html', {'form': form})
            
            # Instantiate the correct restriction based on the type.
            if rtype == 'DateExclusionRestriction':
                instance = DateExclusionRestriction(name=name, description=description, parameters=parameters)
            elif rtype == 'AdjacentDayRestriction':
                instance = AdjacentDayRestriction(name=name, description=description, parameters=parameters)
            elif rtype == 'ConsecutiveDayRestriction':
                instance = ConsecutiveDayRestriction(name=name, description=description, parameters=parameters)
            elif rtype == 'CoworkerRestriction':
                instance = CoworkerRestriction(name=name, description=description, parameters=parameters)
            elif rtype == 'DayOfWeekRestriction':
                instance = DayOfWeekRestriction(name=name, description=description, parameters=parameters)
            elif rtype == 'PeriodLimitRestriction':
                instance = PeriodLimitRestriction(name=name, description=description, parameters=parameters)
            else:
                return HttpResponse("Unknown restriction type", status=400)
            
            # Optional: Resolve category and location associations if needed.
            if category:
                instance.category_id = category  # Assuming the value provided matches an existing Category ID.
            if location:
                instance.location_id = location  # Similarly for Location.
            
            instance.save()
            return redirect('hr_restriction_list')
    else:
        form = RestrictionForm()
    
    return render(request, 'leave/hr_restriction_form.html', {'form': form})
