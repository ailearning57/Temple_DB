from django.contrib import admin
from .models import Donation, Expense, BulkDonationUpload, BulkExpenseUpload

# -- OCR MODULES DEPRECATED PER USER REQUEST -- 
# from deep_translator import GoogleTranslator
# import pytesseract
# ---------------------------------------------

from PIL import Image
import os
import logging
import re
from django.contrib import messages
from io import BytesIO
from django.core.files.base import ContentFile
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

logger = logging.getLogger(__name__)

# Explicitly map the Tesseract executable path for Windows
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

@admin.action(description="Generate Missing PDF Receipts for selected Donations")
def generate_missing_receipts(modeladmin, request, queryset):
    generated = 0
    for obj in queryset:
        if not obj.receipt_pdf:
            obj.save() # The save() method auto-generates the receipt
            generated += 1
    messages.success(request, f"Successfully auto-generated {generated} missing receipts.")

@admin.action(description="Generate Missing Master PDFs for selected Bulk Uploads")
def generate_missing_master_pdfs(modeladmin, request, queryset):
    generated = 0
    from io import BytesIO
    from django.core.files.base import ContentFile
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter

    for obj in queryset:
        if not obj.master_receipts_pdf and obj.is_processed:
            donations = Donation.objects.filter(description=f"Generated from Bulk File Upload: {obj.title}", is_deleted=False)
            if donations.exists():
                buffer = BytesIO()
                p = canvas.Canvas(buffer, pagesize=letter)
                for d in donations:
                    p.setFont("Helvetica-Bold", 24)
                    p.drawString(100, 750, "Temple Trust - Official Donor Receipt")
                    p.setFont("Helvetica", 12)
                    p.drawString(100, 700, f"Receipt ID: DON-{d.pk}")
                    try:
                        p.drawString(100, 680, f"Date: {d.date.strftime('%Y-%m-%d')}")
                    except:
                        p.drawString(100, 680, "Date: Record Date")
                    p.drawString(100, 660, f"Donor Name: {d.title}")
                    p.drawString(100, 640, f"Donation Amount: INR {d.amount}")
                    p.drawString(100, 580, "Thank you very much for your generous contribution!")
                    p.showPage()
                p.save()
                
                pdf_name = f"bulk_master_receipts_{obj.pk}.pdf"
                obj.master_receipts_pdf.save(pdf_name, ContentFile(buffer.getvalue()), save=False)
                obj.save(update_fields=['master_receipts_pdf'])
                generated += 1
                
    messages.success(request, f"Successfully auto-generated {generated} missing Master PDFs for Bulk Uploads.")

@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ('title', 'amount', 'date', 'created_by')
    list_filter = ('date',)
    search_fields = ('title', 'description')
    actions = [generate_missing_receipts]

    def get_queryset(self, request):
        return super().get_queryset(request).filter(is_deleted=False)
        
    def delete_queryset(self, request, queryset):
        queryset.update(is_deleted=True)

@admin.action(description="Mark selected Expenses as Cleared (Paid)")
def mark_expenses_cleared(modeladmin, request, queryset):
    updated = queryset.update(status='CLEARED')
    messages.success(request, f"Successfully cleared {updated} expenses.")

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('title', 'amount', 'date', 'status', 'has_receipt', 'created_by')
    list_filter = ('status', 'date', 'created_by')
    search_fields = ('title', 'description', 'extracted_text')
    actions = [mark_expenses_cleared]

    def get_queryset(self, request):
        return super().get_queryset(request).filter(is_deleted=False)
        
    def delete_queryset(self, request, queryset):
        queryset.update(is_deleted=True)

    def has_receipt(self, obj):
        return bool(obj.receipt_image)
    has_receipt.boolean = True
    has_receipt.short_description = 'Receipt Attached'

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        
        # OCR DISABLED
        # if 'receipt_image' in form.changed_data and obj.receipt_image:
        #     try:
        #         img_path = obj.receipt_image.path
        #         if os.path.exists(img_path):
        #             raw_text = pytesseract.image_to_string(Image.open(img_path))
        #             if raw_text.strip():
        #                 translated = GoogleTranslator(source='auto', target='en').translate(raw_text)
        #                 obj.extracted_text = f"** ORIGINAL **\n{raw_text}\n\n** TRANSLATED (English) **\n{translated}"
        #             else:
        #                 obj.extracted_text = "[No text successfully detected]"
        #             obj.save(update_fields=['extracted_text'])
        #     except Exception as e:
        #         logger.error(f"OCR Error: {e}")
        #         obj.extracted_text = f"OCR Error: {str(e)}\n\n(Ensure Tesseract-OCR is installed on the system and in your PATH)"
        #         obj.save(update_fields=['extracted_text'])

import pandas as pd

@admin.register(BulkDonationUpload)
class BulkDonationUploadAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_at', 'is_processed', 'created_by')
    readonly_fields = ('is_processed',)
    exclude = ('list_image',)  # Hide the deprecated OCR image field from the admin interface
    actions = [generate_missing_master_pdfs]
    
    def get_queryset(self, request):
        return super().get_queryset(request).filter(is_deleted=False)
        
    def delete_queryset(self, request, queryset):
        queryset.update(is_deleted=True)
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        
        # 1. File uploaded but no parsed data yet -> Parse the file
        if 'data_file' in form.changed_data and obj.data_file and not obj.parsed_data:
            try:
                file_path = obj.data_file.path
                if os.path.exists(file_path):
                    ext = os.path.splitext(file_path)[1].lower()
                    parsed_lines = []
                    df = None
                    
                    if ext in ['.csv']:
                        df = pd.read_csv(file_path)
                    elif ext in ['.xls', '.xlsx']:
                        df = pd.read_excel(file_path)
                    elif ext in ['.txt']:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                            amount_pattern = re.compile(r'\b\d+(?:\.\d{1,2})?\b')
                            for line in lines:
                                line = line.strip()
                                if not line: continue
                                matches = amount_pattern.findall(line)
                                if matches:
                                    amount_str = matches[-1]
                                    name = line.replace(amount_str, '').strip(' -:,._')
                                    if not name: name = "Unknown Donor"
                                    parsed_lines.append(f"{name}: {amount_str}")
                                else:
                                    parsed_lines.append(f"{line}: 0.00")
                    else:
                        raise ValueError(f"Unsupported file extension: {ext}")
                        
                    # Handle tabular DataFrame parsing
                    if df is not None:
                        cols = [str(c).lower() for c in df.columns]
                        name_col = None
                        amount_col = None
                        
                        # Soft-match column names
                        for original_col, lower_col in zip(df.columns, cols):
                            if 'name' in lower_col or 'donor' in lower_col or 'person' in lower_col:
                                name_col = original_col
                            if 'amount' in lower_col or 'rupee' in lower_col or 'val' in lower_col or 'rs' in lower_col or 'donate' in lower_col:
                                amount_col = original_col
                                
                        if not name_col and len(df.columns) > 0: name_col = df.columns[0]
                        if not amount_col and len(df.columns) > 1: amount_col = df.columns[1]
                        
                        # Process generic row formats
                        if len(df.columns) == 1:
                            for idx, row in df.iterrows():
                                val = str(row.iloc[0])
                                amount_pattern = re.compile(r'\b\d+(?:\.\d{1,2})?\b')
                                matches = amount_pattern.findall(val)
                                if matches:
                                    amount_str = matches[-1]
                                    name = val.replace(amount_str, '').strip(' -:,._')
                                    parsed_lines.append(f"{name}: {amount_str}")
                                else:
                                    parsed_lines.append(f"{val}: 0.00")
                        else:
                            import math
                            for idx, row in df.iterrows():
                                name_val = str(row[name_col]).strip() if name_col and not (isinstance(row[name_col], float) and math.isnan(row[name_col])) else "Unknown Name"
                                amount_val = str(row[amount_col]).strip() if amount_col and not (isinstance(row[amount_col], float) and math.isnan(row[amount_col])) else "0"
                                
                                amount_clean = re.sub(r'[^\d.]', '', amount_val)
                                if not amount_clean: amount_clean = "0"
                                
                                parsed_lines.append(f"{name_val}: {amount_clean}")
                                
                    if parsed_lines:
                        obj.parsed_data = "\n".join(parsed_lines)
                        obj.save(update_fields=['parsed_data'])
                        messages.info(request, "File successfully parsed! Please review the Extracted Data closely, check 'Generate Donations' and hit Save!")
                    else:
                        obj.parsed_data = "Error: Found no extractable rows in file."
                        obj.save(update_fields=['parsed_data'])
                        
            except Exception as e:
                logger.error(f"Bulk File Parsing Error: {e}")
                obj.parsed_data = f"File Parsing Error: {str(e)}\nMake sure it's a valid CSV, Excel, or TXT file."
                obj.save(update_fields=['parsed_data'])
                
        # 2. Generate Donations if verified and requested
        if obj.generate_donations and not obj.is_processed and obj.parsed_data:
            lines = obj.parsed_data.split('\n')
            created_donations = []
            for line in lines:
                if ':' in line:
                    parts = line.split(':', 1)
                    name = parts[0].strip()
                    amount_str = parts[1].strip()
                    try:
                        amount_val = float(amount_str)
                        d = Donation.objects.create(
                            title=name if name else "Bulk Donation",
                            description=f"Generated from Bulk File Upload: {obj.title}",
                            amount=amount_val,
                            created_by=request.user
                        )
                        created_donations.append(d)
                    except ValueError:
                        pass
            
            # Combine all into one massive PDF!
            if created_donations:
                from io import BytesIO
                from django.core.files.base import ContentFile
                from reportlab.pdfgen import canvas
                from reportlab.lib.pagesizes import letter
                
                buffer = BytesIO()
                p = canvas.Canvas(buffer, pagesize=letter)
                for d in created_donations:
                    p.setFont("Helvetica-Bold", 24)
                    p.drawString(100, 750, "Temple Trust - Official Donor Receipt")
                    p.setFont("Helvetica", 12)
                    p.drawString(100, 700, f"Receipt ID: DON-{d.pk}")
                    try:
                        p.drawString(100, 680, f"Date: {d.date.strftime('%Y-%m-%d')}")
                    except:
                        p.drawString(100, 680, "Date: Record Date")
                    p.drawString(100, 660, f"Donor Name: {d.title}")
                    p.drawString(100, 640, f"Donation Amount: INR {d.amount}")
                    p.drawString(100, 580, "Thank you very much for your generous contribution!")
                    p.showPage() # jump to next page
                p.save()
                
                pdf_name = f"bulk_master_receipts_{obj.pk}.pdf"
                obj.master_receipts_pdf.save(pdf_name, ContentFile(buffer.getvalue()), save=False)
            
            obj.is_processed = True
            obj.save(update_fields=['is_processed', 'master_receipts_pdf'])
            messages.success(request, f"Successfully created {len(created_donations)} Donation records and compiled their Master PDF receipt file!")

@admin.register(BulkExpenseUpload)
class BulkExpenseUploadAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_at', 'is_processed', 'created_by')
    readonly_fields = ('is_processed',)
    
    def get_queryset(self, request):
        return super().get_queryset(request).filter(is_deleted=False)
        
    def delete_queryset(self, request, queryset):
        queryset.update(is_deleted=True)
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        
        # 1. File uploaded but no parsed data yet -> Parse the file
        if 'data_file' in form.changed_data and obj.data_file and not obj.parsed_data:
            try:
                file_path = obj.data_file.path
                if os.path.exists(file_path):
                    ext = os.path.splitext(file_path)[1].lower()
                    parsed_lines = []
                    df = None
                    
                    if ext in ['.csv']:
                        df = pd.read_csv(file_path)
                    elif ext in ['.xls', '.xlsx']:
                        df = pd.read_excel(file_path)
                    elif ext in ['.txt']:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                            amount_pattern = re.compile(r'\b\d+(?:\.\d{1,2})?\b')
                            for line in lines:
                                line = line.strip()
                                if not line: continue
                                matches = amount_pattern.findall(line)
                                if matches:
                                    amount_str = matches[-1]
                                    name = line.replace(amount_str, '').strip(' -:,._')
                                    if not name: name = "Unknown Expense"
                                    parsed_lines.append(f"{name}: {amount_str}")
                                else:
                                    parsed_lines.append(f"{line}: 0.00")
                    else:
                        raise ValueError(f"Unsupported file extension: {ext}")
                        
                    # Handle tabular DataFrame parsing
                    if df is not None:
                        cols = [str(c).lower() for c in df.columns]
                        name_col = None
                        amount_col = None
                        
                        # Soft-match column names
                        for original_col, lower_col in zip(df.columns, cols):
                            if 'name' in lower_col or 'desc' in lower_col or 'item' in lower_col or 'title' in lower_col or 'cost' in lower_col:
                                name_col = original_col
                            if 'amount' in lower_col or 'price' in lower_col or 'val' in lower_col or 'rs' in lower_col or 'rupee' in lower_col:
                                amount_col = original_col
                                
                        if not name_col and len(df.columns) > 0: name_col = df.columns[0]
                        if not amount_col and len(df.columns) > 1: amount_col = df.columns[1]
                        
                        # Process generic row formats
                        if len(df.columns) == 1:
                            for idx, row in df.iterrows():
                                val = str(row.iloc[0])
                                amount_pattern = re.compile(r'\b\d+(?:\.\d{1,2})?\b')
                                matches = amount_pattern.findall(val)
                                if matches:
                                    amount_str = matches[-1]
                                    name = val.replace(amount_str, '').strip(' -:,._')
                                    parsed_lines.append(f"{name}: {amount_str}")
                                else:
                                    parsed_lines.append(f"{val}: 0.00")
                        else:
                            import math
                            for idx, row in df.iterrows():
                                name_val = str(row[name_col]).strip() if name_col and not (isinstance(row[name_col], float) and math.isnan(row[name_col])) else "Unknown Expense Item"
                                amount_val = str(row[amount_col]).strip() if amount_col and not (isinstance(row[amount_col], float) and math.isnan(row[amount_col])) else "0"
                                
                                amount_clean = re.sub(r'[^\d.]', '', amount_val)
                                if not amount_clean: amount_clean = "0"
                                
                                parsed_lines.append(f"{name_val}: {amount_clean}")
                                
                    if parsed_lines:
                        obj.parsed_data = "\n".join(parsed_lines)
                        obj.save(update_fields=['parsed_data'])
                        messages.info(request, "File successfully parsed! Please review the Extracted Data closely, check 'Generate Expenses' and hit Save!")
                    else:
                        obj.parsed_data = "Error: Found no extractable rows in file."
                        obj.save(update_fields=['parsed_data'])
                        
            except Exception as e:
                logger.error(f"Bulk Expense Parsing Error: {e}")
                obj.parsed_data = f"File Parsing Error: {str(e)}\nMake sure it's a valid CSV, Excel, or TXT file."
                obj.save(update_fields=['parsed_data'])
                
        # 2. Generate Expenses if verified and requested
        if obj.generate_expenses and not obj.is_processed and obj.parsed_data:
            lines = obj.parsed_data.split('\n')
            created_count = 0
            for line in lines:
                if ':' in line:
                    parts = line.split(':', 1)
                    name = parts[0].strip()
                    amount_str = parts[1].strip()
                    try:
                        amount_val = float(amount_str)
                        Expense.objects.create(
                            title=name if name else "Bulk Expense",
                            description=f"Generated from Bulk File Upload: {obj.title}",
                            amount=amount_val,
                            created_by=request.user
                        )
                        created_count += 1
                    except ValueError:
                        pass
            
            obj.is_processed = True
            obj.save(update_fields=['is_processed'])
            messages.success(request, f"Successfully created {created_count} individual Expense records from the file!")
