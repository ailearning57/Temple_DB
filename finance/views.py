from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import FinanceRecord

@login_required
def finance_list(request):
    records = FinanceRecord.objects.all().order_by('-date')
    
    total_donations = sum(r.amount for r in records if r.record_type == 'DONATION')
    total_expenditures = sum(r.amount for r in records if r.record_type == 'EXPENDITURE')
    balance = total_donations - total_expenditures

    return render(request, 'finance/record_list.html', {
        'records': records,
        'total_donations': total_donations,
        'total_expenditures': total_expenditures,
        'balance': balance,
    })
