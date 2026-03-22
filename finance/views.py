from django.shortcuts import render
from .models import Donation, Expense
from itertools import chain
from operator import attrgetter

def finance_list(request):
    selected_year = request.GET.get('year', 'all')
    donations_qs = Donation.objects.filter(is_deleted=False)
    expenses_qs = Expense.objects.filter(is_deleted=False)
    
    # Get distinct active years
    d_years = donations_qs.dates('date', 'year')
    e_years = expenses_qs.dates('date', 'year')
    available_years = sorted(list(set(
        [d.year for d in d_years] + [e.year for e in e_years]
    )), reverse=True)
    
    # Filter by year if requested
    if selected_year != 'all' and selected_year.isdigit():
        donations_qs = donations_qs.filter(date__year=int(selected_year))
        expenses_qs = expenses_qs.filter(date__year=int(selected_year))
        
    donations = list(donations_qs)
    expenses = list(expenses_qs)
    
    # Tag them for the template
    for d in donations:
        d.record_type = 'DONATION'
    for e in expenses:
        e.record_type = 'EXPENDITURE'
    
    # Combine and sort by date descending
    records = sorted(
        chain(donations, expenses),
        key=attrgetter('date'),
        reverse=True
    )
    
    total_donations = sum(d.amount for d in donations)
    total_expenditures = sum(e.amount for e in expenses)
    balance = total_donations - total_expenditures

    return render(request, 'finance/record_list.html', {
        'records': records,
        'total_donations': total_donations,
        'total_expenditures': total_expenditures,
        'balance': balance,
        'available_years': available_years,
        'selected_year': selected_year,
    })

# --- NEW MODULAR VIEWS ---

def donations_list(request):
    selected_year = request.GET.get('year', 'all')
    donations_qs = Donation.objects.filter(is_deleted=False)
    
    available_years = sorted(list(donations_qs.dates('date', 'year').values_list('date__year', flat=True)), reverse=True)
    
    if selected_year != 'all' and selected_year.isdigit():
        donations_qs = donations_qs.filter(date__year=int(selected_year))
        
    donations = list(donations_qs.order_by('-date'))
    total_donations = sum(d.amount for d in donations)
    
    return render(request, 'finance/donations_list.html', {
        'donations': donations,
        'total_donations': total_donations,
        'available_years': available_years,
        'selected_year': selected_year,
    })

def expenses_list(request):
    selected_year = request.GET.get('year', 'all')
    expenses_qs = Expense.objects.filter(is_deleted=False)
    
    available_years = sorted(list(expenses_qs.dates('date', 'year').values_list('date__year', flat=True)), reverse=True)
    
    if selected_year != 'all' and selected_year.isdigit():
        expenses_qs = expenses_qs.filter(date__year=int(selected_year))
        
    expenses = list(expenses_qs.order_by('-date'))
    total_expenditures = sum(e.amount for e in expenses if e.status == 'CLEARED')
    total_pending_dues = sum(e.amount for e in expenses if e.status == 'PENDING')
    
    return render(request, 'finance/expenses_list.html', {
        'expenses': expenses,
        'total_expenditures': total_expenditures,
        'total_pending_dues': total_pending_dues,
        'available_years': available_years,
        'selected_year': selected_year,
    })

def consolidated_dashboard(request):
    donations_qs = Donation.objects.filter(is_deleted=False)
    expenses_qs = Expense.objects.filter(is_deleted=False)
    
    export_format = request.GET.get('export')
    if export_format in ['csv', 'excel']:
        # Strict Admin-Only Security Check
        if not (request.user.is_authenticated and (request.user.is_staff or getattr(request.user, 'role', '') == 'ADMIN')):
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("You must be an administrator to strategically export financial data.")
            
        import pandas as pd
        from django.http import HttpResponse
        
        d_data = [{'ID': f'DON-{d.pk}', 'Type': 'Donation', 'Date': d.date.strftime('%Y-%m-%d'), 'Title': d.title, 'Amount': d.amount, 'Status': 'CLEARED'} for d in donations_qs.order_by('-date')]
        e_data = [{'ID': f'EXP-{e.pk}', 'Type': 'Expense', 'Date': e.date.strftime('%Y-%m-%d'), 'Title': e.title, 'Amount': e.amount, 'Status': e.status} for e in expenses_qs.order_by('-date')]
        
        df = pd.DataFrame(d_data + e_data)
        if not df.empty:
            df = df.sort_values('Date', ascending=False)
        
        if export_format == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="temple_finance_ledger.csv"'
            df.to_csv(path_or_buf=response, index=False)
            return response
        elif export_format == 'excel':
            response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = 'attachment; filename="temple_finance_ledger.xlsx"'
            df.to_excel(response, index=False, engine='openpyxl')
            return response
            
    d_years = list(donations_qs.dates('date', 'year').values_list('date__year', flat=True))
    e_years = list(expenses_qs.dates('date', 'year').values_list('date__year', flat=True))
    available_years = sorted(list(set(d_years + e_years)), reverse=True)
    
    yearly_data = []
    for y in available_years:
        d_total = sum(d.amount for d in donations_qs.filter(date__year=y))
        
        e_qs_year = expenses_qs.filter(date__year=y)
        e_cleared = sum(e.amount for e in e_qs_year if e.status == 'CLEARED')
        e_pending = sum(e.amount for e in e_qs_year if e.status == 'PENDING')
        
        yearly_data.append({
            'year': y,
            'donations': d_total,
            'expenses': e_cleared,
            'pending_dues': e_pending,
            'balance': d_total - e_cleared
        })
        
    all_time_donations = sum(d.amount for d in donations_qs)
    all_time_expenses = sum(e.amount for e in expenses_qs if e.status == 'CLEARED')
    all_time_pending = sum(e.amount for e in expenses_qs if e.status == 'PENDING')
    all_time_balance = all_time_donations - all_time_expenses
    
    return render(request, 'finance/consolidated.html', {
        'yearly_data': yearly_data,
        'all_time_donations': all_time_donations,
        'all_time_expenses': all_time_expenses,
        'all_time_pending': all_time_pending,
        'all_time_balance': all_time_balance,
    })
