from django.db import models
from django.utils import timezone
from users.models import User

class Transaction(models.fields.Field):
    # We will use simple models for now. For encryption, django-cryptography can be applied
    # to specific fields if imported: from django_cryptography.fields import encrypt
    pass

class FinanceRecord(models.Model):
    TYPE_CHOICES = (
        ('DONATION', 'Donation'),
        ('EXPENDITURE', 'Expenditure'),
    )
    
    record_type = models.CharField(max_length=15, choices=TYPE_CHOICES)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField(default=timezone.now)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Example of how encrypted field would look
    # donor_details = encrypt(models.TextField(blank=True, null=True))

    def __str__(self):
        return f"{self.get_record_type_display()} - {self.title} - {self.amount}"
