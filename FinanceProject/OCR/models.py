from django.db import models
from django.contrib.auth.models import User

class Receipt(models.Model):
    store_name = models.CharField(max_length=255)
    date = models.DateField(null=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    receipt_image = models.ImageField(upload_to='receipts/', blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

class Expense(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    receipt = models.ForeignKey(Receipt, on_delete=models.CASCADE, related_name='expenses', null=True, blank=True)
    item = models.CharField(max_length=255)  # e.g., 'Burger'
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"Expense of {self.amount} for {self.item} from {self.receipt.store_name}"
    
