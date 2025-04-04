from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('request_editor/', views.request_editor, name='request_editor'),
    path('withdraw_request/<int:request_id>/', views.withdraw_request, name='withdraw_request'),
    path('cancel_request/<int:request_id>/', views.cancel_request, name='cancel_request'),
    path('edit_request/<int:request_id>/', views.edit_request, name='edit_request'),
    # Manager-specific URLs for approving or rejecting requests.
    path('approve_request/<int:request_id>/', views.approve_request, name='approve_request'),
    path('reject_request/<int:request_id>/', views.reject_request, name='reject_request'),
    # HR-specific URLs
    path('hr/restrictions/', views.hr_restriction_list, name='hr_restriction_list'),
    path('hr/restrictions/create/', views.hr_restriction_create, name='hr_restriction_create'),
    # Future: paths for editing and deleting restrictions can be added.
]
