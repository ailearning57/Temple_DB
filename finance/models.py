from django.db import models
from django.utils import timezone
from users.models import User
from io import BytesIO
from django.core.files.base import ContentFile
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from users.models import User

# --- DEPRECATED MODELS ---
# class FinanceRecord(models.Model):
#     TYPE_CHOICES = (
#         ('DONATION', 'Donation'),
#         ('EXPENDITURE', 'Expenditure'),
#     )
#     record_type = models.CharField(max_length=15, choices=TYPE_CHOICES)
#     title = models.CharField(max_length=200)
#     description = models.TextField(blank=True, null=True)
#     amount = models.DecimalField(max_digits=12, decimal_places=2)
#     date = models.DateField(default=timezone.now)
#     created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
#
#     def __str__(self):
#         return f"{self.get_record_type_display()} - {self.title} - {self.amount}"
# -------------------------

class Donation(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField(default=timezone.now)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)
    receipt_pdf = models.FileField(upload_to='receipts/pdfs/', blank=True, null=True, help_text="Auto-generated PDF receipt")
    
    def delete(self, *args, **kwargs):
        self.is_deleted = True
        self.save()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.receipt_pdf and not self.is_deleted:
            buffer = BytesIO()
            p = canvas.Canvas(buffer, pagesize=letter)
            p.setFont("Helvetica-Bold", 24)
            p.drawString(100, 750, "Temple Trust - Official Donor Receipt")
            p.setFont("Helvetica", 12)
            p.drawString(100, 700, f"Receipt ID: DON-{self.pk}")
            try:
                p.drawString(100, 680, f"Date: {self.date.strftime('%Y-%m-%d')}")
            except:
                p.drawString(100, 680, "Date: Record Date")
            p.drawString(100, 660, f"Donor Name: {self.title}")
            p.drawString(100, 640, f"Donation Amount: INR {self.amount}")
            p.drawString(100, 580, "Thank you very much for your generous contribution!")
            p.showPage()
            p.save()
            
            pdf_name = f"receipt_{self.pk}.pdf"
            self.receipt_pdf.save(pdf_name, ContentFile(buffer.getvalue()), save=False)
            super().save(update_fields=['receipt_pdf'])
    
    def __str__(self):
        return f"Donation: {self.title} - ₹{self.amount}"

class Expense(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField(default=timezone.now)
    
    STATUS_CHOICES = (
        ('PENDING', 'Pending (Due)'),
        ('CLEARED', 'Cleared (Paid)'),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='CLEARED')
    
    receipt_image = models.ImageField(upload_to='receipts/', blank=True, null=True)
    extracted_text = models.TextField(blank=True, null=True, help_text="Auto-populated via OCR and translation when an image is uploaded.")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)
    
    def delete(self, *args, **kwargs):
        self.is_deleted = True
        self.save()
    
    def __str__(self):
        return f"Expense: {self.title} - ₹{self.amount}"

class BulkDonationUpload(models.Model):
    title = models.CharField(max_length=200, default="Bulk Upload")
    list_image = models.ImageField(upload_to='bulk_donations/', blank=True, null=True) # DEPRECATED per architecture rule
    data_file = models.FileField(upload_to='bulk_donations/files/', blank=True, null=True, help_text="Upload CSV, Excel (.xlsx), or TXT file with your donor list.")
    parsed_data = models.TextField(blank=True, null=True, help_text="Review and edit the extracted list here. Format: 'Name: Amount' (one per line).")
    generate_donations = models.BooleanField(default=False, help_text="Check this box and save to generate individual Donation records from the parsed data above.")
    is_processed = models.BooleanField(default=False, editable=False)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)
    master_receipts_pdf = models.FileField(upload_to='receipts/bulk/', blank=True, null=True, help_text="Combined Multi-Page PDF of all generated receipts")

    def delete(self, *args, **kwargs):
        self.is_deleted = True
        self.save()

    def __str__(self):
        return f"{self.title} - {self.created_at.strftime('%Y-%m-%d')}"

class BulkExpenseUpload(models.Model):
    title = models.CharField(max_length=200, default="Bulk Expenses Upload")
    data_file = models.FileField(upload_to='bulk_expenses/files/', blank=True, null=True, help_text="Upload CSV, Excel (.xlsx), or TXT file with your expense list.")
    parsed_data = models.TextField(blank=True, null=True, help_text="Review and edit the extracted list here. Format: 'Cost Description: Amount' (one per line).")
    generate_expenses = models.BooleanField(default=False, help_text="Check this box and save to generate individual Expense records from the parsed data above.")
    is_processed = models.BooleanField(default=False, editable=False)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)

    def delete(self, *args, **kwargs):
        self.is_deleted = True
        self.save()

    def __str__(self):
        return f"{self.title} - {self.created_at.strftime('%Y-%m-%d')}"
