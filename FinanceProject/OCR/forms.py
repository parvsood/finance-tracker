# forms.py
from django import forms
from .models import Receipt

class ReceiptForm(forms.ModelForm):
    class Meta:
        model = Receipt
        fields = ['store_name', 'date', 'total_amount', 'receipt_image']

class ReceiptEditForm(forms.Form):
    store_name = forms.CharField(max_length=255, required=True)
    total_amount = forms.DecimalField(max_digits=10, decimal_places=2, required=True)
    date = forms.DateField(required=True)
    items = forms.CharField(widget=forms.Textarea, required=True)

class ReceiptUploadOnlyForm(forms.ModelForm):
    class Meta:
        model = Receipt
        fields = ['receipt_image']
