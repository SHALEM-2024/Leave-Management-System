# leave/templatetags/custom_filters.py

from django import template

register = template.Library()

@register.filter
def get_class_name(obj):
    """Return the class name of an object."""
    return obj.__class__.__name__
