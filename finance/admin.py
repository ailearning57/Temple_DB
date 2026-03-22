from django.contrib import admin
from .models import FinanceRecord

@admin.register(FinanceRecord)
class FinanceRecordAdmin(admin.ModelAdmin):
    list_display = ('title', 'record_type', 'amount', 'date', 'created_by')
    list_filter = ('record_type', 'date')
    search_fields = ('title', 'description')
