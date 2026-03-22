from django.contrib import admin
from .models import TempleInfo, Event

@admin.register(TempleInfo)
class TempleInfoAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_email', 'contact_phone')

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'date', 'is_active')
    list_filter = ('is_active', 'date')
