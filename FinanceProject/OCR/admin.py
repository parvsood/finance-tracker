from django.contrib import admin
from .models import Receipt, Expense

# Register your models here.
admin.site.register(Receipt)
admin.site.register(Expense)