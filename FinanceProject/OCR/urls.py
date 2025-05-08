from django.urls import path
from . import views

urlpatterns = [
    path('upload/', views.upload_receipt, name='upload_receipt'),
    path('save-receipt/', views.save_receipt_data, name='save_receipt_data'),
]
