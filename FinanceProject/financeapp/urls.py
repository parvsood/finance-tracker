from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('about/', views.about, name='about'),
    path('about_us/', views.about_us, name='about_us'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register, name='register'),
    path('userauth/', views.userauth, name='userauth'),
    path('transactions/', views.transactions_view, name='transactions'),
    path('add_transaction/', views.add_transaction, name='add_transaction'),
    path('edit/<int:transaction_id>/', views.edit_transaction, name='edit_transaction'),
    path('delete_transaction/<int:transaction_id>/', views.delete_transaction, name='delete_transaction'),
    path('statistics/', views.statistics, name='statistics'),
    path('daily_spending_data/', views.daily_spending_data, name='daily_spending_data'),
    path('monthly_spending_data/', views.monthly_spending_data, name='monthly_spending_data'),
    path('features/', views.features, name='features'),
    path('learn_more/', views.learn_more, name='learn_more'),
    path('discover_more/', views.discover_more, name='discover_more'),
    path('explore_more/', views.explore_more, name='explore_more'),
    path('view_trends/', views.view_trends, name='view_trends'),
    # Add a new URL pattern for recent transactions
    path('recent-transactions/', views.recent_transactions, name='recent_transactions'),
    path('income_expense_data/', views.income_expense_data, name='income_expense_data'),
    path('category_data/', views.category_data, name='category_data'),
    path('payment_method_data/', views.payment_method_data, name='payment_method_data'),
]
