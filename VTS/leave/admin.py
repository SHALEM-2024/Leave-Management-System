from django.contrib import admin


from .models import User, Location, Category, Grant, Request, DateExclusionRestriction, AdjacentDayRestriction, ConsecutiveDayRestriction, CoworkerRestriction, DayOfWeekRestriction, PeriodLimitRestriction

# Register your models here.
admin.site.register(User)
admin.site.register(Location)
admin.site.register(Category)
admin.site.register(Grant)
admin.site.register(Request)
admin.site.register(DateExclusionRestriction)
admin.site.register(AdjacentDayRestriction)
admin.site.register(ConsecutiveDayRestriction)
admin.site.register(CoworkerRestriction)
admin.site.register(DayOfWeekRestriction)
admin.site.register(PeriodLimitRestriction)

