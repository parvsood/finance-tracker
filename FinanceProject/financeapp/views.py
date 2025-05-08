from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from datetime import datetime
from .models import UserProfile, Transaction, User, ContactSubmission
from django.db import models
from django.contrib.auth import authenticate, login
import requests
import json
from django.conf import settings
import os
# Add this new view function for income vs expense data
from datetime import datetime, timedelta
from django.db.models import Sum
from django.db.models.functions import TruncMonth, TruncWeek
from django.utils import timezone

# Flask API URL
API_URL = "http://localhost:5000/api"

def index(request):
    if request.method == 'POST' and 'contact_form' in request.POST:
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        message = request.POST.get('message')
        
        if all([first_name, last_name, email, message]):
            ContactSubmission.objects.create(
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                message=message
            )
            messages.success(request, 'Your message has been sent successfully. We will get back to you soon!')
        else:
            messages.error(request, 'Please fill in all required fields.')
            
    return render(request, 'index.html')

def userauth(request):
    return render(request, 'userauth.html')

def dashboard(request):
    if 'username' in request.session:
        user_id = request.session['user_id']
        username = request.session['username']
        token = request.session.get('api_token')
        
        try:
            # Try to get data from API
            headers = {'Authorization': f'Bearer {token}'} if token else {}
            response = requests.get(f"{API_URL}/dashboard", headers=headers, params={'user_id': user_id})
            
            if response.status_code == 200:
                data = response.json()
                
                # Calculate income and expense totals
                income_total = sum(t['amount'] for t in data.get('transactions', []) if t['transaction_type'] == 'Income')
                expense_total = sum(t['amount'] for t in data.get('transactions', []) if t['transaction_type'] == 'Expense')
                
                # Define total_amount as income minus expense
                total_amount = income_total - expense_total
                
                # Calculate percentages for progress bars
                total = total_amount if total_amount > 0 else 1
                upi_percentage = (data['total_upi'] / total) * 100 if data['total_upi'] > 0 else 0
                cash_percentage = (data['total_cash'] / total) * 100 if data['total_cash'] > 0 else 0
                
                # Calculate net savings and savings percentage
                net_savings = income_total - expense_total
                savings_percentage = (net_savings / income_total) * 100 if income_total > 0 else 0
                
                return render(request, 'dashboard.html', {
                    'username': username,
                    'total_amount': total_amount,
                    'total_upi': data['total_upi'],
                    'total_cash': data['total_cash'],
                    'upi_percentage': round(upi_percentage, 1),
                    'cash_percentage': round(cash_percentage, 1),
                    'income_total': income_total,
                    'expense_total': expense_total,
                    'net_savings': net_savings,
                    'savings_percentage': round(savings_percentage, 1),
                    'api_status': 'connected'
                })
            else:
                # API request failed, fall back to direct database access
                from django.db import transaction
                
                with transaction.atomic():
                    transactions = Transaction.objects.filter(user_id=user_id)
                    
                    # Calculate income and expense totals
                    income_transactions = transactions.filter(transaction_type='Income')
                    expense_transactions = transactions.filter(transaction_type='Expense')
                    income_total = sum(t.amount for t in income_transactions)
                    expense_total = sum(t.amount for t in expense_transactions)
                    
                    # Define total_amount as income minus expense
                    total_amount = income_total - expense_total
                    
                    # Calculate UPI and Cash totals
                    total_upi = sum(t.amount for t in transactions if t.payment_method == 'UPI')
                    total_cash = sum(t.amount for t in transactions if t.payment_method == 'Cash')
                    
                    # Calculate percentages for progress bars
                    total = total_amount if total_amount > 0 else 1
                    upi_percentage = min((total_upi / total) * 100 if total_upi > 0 else 0, 100)  # Cap at 100%
                    cash_percentage = min((total_cash / total) * 100 if total_cash > 0 else 0, 100)  # Cap at 100%
                    
                    # Calculate net savings and savings percentage
                    net_savings = income_total - expense_total
                    savings_percentage = min((net_savings / income_total) * 100 if income_total > 0 else 0, 100)  # Cap at 100%
                
                return render(request, 'dashboard.html', {
                    'username': username,
                    'total_amount': total_amount,
                    'total_upi': total_upi,
                    'total_cash': total_cash,
                    'upi_percentage': round(upi_percentage, 1),
                    'cash_percentage': round(cash_percentage, 1),
                    'income_total': income_total,
                    'expense_total': expense_total,
                    'net_savings': net_savings,
                    'savings_percentage': round(savings_percentage, 1),
                    'api_status': 'disconnected'
                })
        except requests.exceptions.RequestException:
            # API is down, fall back to direct database access
            from django.db import transaction
            
            with transaction.atomic():
                transactions = Transaction.objects.filter(user_id=user_id)
                
                # Calculate income and expense totals
                income_transactions = transactions.filter(transaction_type='Income')
                expense_transactions = transactions.filter(transaction_type='Expense')
                income_total = sum(t.amount for t in income_transactions)
                expense_total = sum(t.amount for t in expense_transactions)
                
                # Define total_amount as income minus expense
                total_amount = income_total - expense_total
                
                # Calculate UPI and Cash totals
                total_upi = sum(t.amount for t in transactions if t.payment_method == 'UPI')
                total_cash = sum(t.amount for t in transactions if t.payment_method == 'Cash')
                
                # Calculate percentages for progress bars
                total = total_amount if total_amount > 0 else 1
                upi_percentage = min((total_upi / total) * 100 if total_upi > 0 else 0, 100)  # Cap at 100%
                cash_percentage = min((total_cash / total) * 100 if total_cash > 0 else 0, 100)  # Cap at 100%
                
                # Calculate net savings and savings percentage
                net_savings = income_total - expense_total
                savings_percentage = min((net_savings / income_total) * 100 if income_total > 0 else 0, 100)  # Cap at 100%
            
            return render(request, 'dashboard.html', {
                'username': username,
                'total_amount': total_amount,
                'total_upi': total_upi,
                'total_cash': total_cash,
                'upi_percentage': round(upi_percentage, 1),
                'cash_percentage': round(cash_percentage, 1),
                'income_total': income_total,
                'expense_total': expense_total,
                'net_savings': net_savings,
                'savings_percentage': round(savings_percentage, 1),
                'api_status': 'disconnected'
            })
    return redirect('login')

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        try:
            # Try to authenticate via API
            response = requests.post(f"{API_URL}/auth", json={
                'username': username,
                'password': password
            })
            
            if response.status_code == 200:
                data = response.json()
                user = authenticate(request, username=username, password=password)
                if user:
                    login(request, user)
                    request.session['user_id'] = user.id
                    request.session['username'] = username
                    request.session['api_token'] = data.get('token')
                    return redirect('dashboard')
            
            # If API authentication fails or API is down, fall back to Django authentication
            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                request.session['user_id'] = user.id
                request.session['username'] = user.username
                return redirect('dashboard')
            else:
                messages.error(request, 'Invalid username or password.')
        except requests.exceptions.RequestException:
            # API is down, use Django authentication
            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                request.session['user_id'] = user.id
                request.session['username'] = user.username
                return redirect('dashboard')
            else:
                messages.error(request, 'Invalid username or password.')
    
    return render(request, 'login.html')

def logout_view(request):
    request.session.flush()
    return redirect('index')

# Modify the register function to handle database connections better and prevent locking
def register(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        phone = request.POST['phone']
        password = request.POST['password']

        # Check if username already exists before trying to create
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return render(request, 'register.html')

        try:
            # Try to register via API
            try:
                response = requests.post(f"{API_URL}/register", json={
                    'username': username,
                    'email': email,
                    'phone': phone,
                    'password': password
                })
                
                if response.status_code == 201:
                    # Auto-login the user after successful registration
                    user = authenticate(request, username=username, password=password)
                    if user:
                        login(request, user)
                        request.session['user_id'] = user.id
                        request.session['username'] = username
                        
                        # Try to get API token
                        auth_response = requests.post(f"{API_URL}/auth", json={
                            'username': username,
                            'password': password
                        })
                        
                        if auth_response.status_code == 200:
                            data = auth_response.json()
                            request.session['api_token'] = data.get('token')
                        
                        return redirect('dashboard')
                    else:
                        messages.success(request, 'Registration successful. Please log in.')
                        return redirect('login')
                elif response.status_code == 400:
                    data = response.json()
                    messages.error(request, data.get('message', 'Registration failed.'))
                else:
                    # Fall back to Django registration
                    from django.db import transaction
                    
                    # Use transaction to prevent database locking
                    with transaction.atomic():
                        user = User.objects.create_user(username=username, email=email, password=password)
                        UserProfile.objects.create(user=user, phone=phone)
                    
                    # Auto-login the user after successful registration
                    user = authenticate(request, username=username, password=password)
                    if user:
                        login(request, user)
                        request.session['user_id'] = user.id
                        request.session['username'] = username
                        return redirect('dashboard')
                    else:
                        messages.success(request, 'Registration successful. Please log in.')
                        return redirect('login')
            except requests.exceptions.RequestException:
                # API is down, use Django registration
                from django.db import transaction
                
                # Use transaction to prevent database locking
                with transaction.atomic():
                    user = User.objects.create_user(username=username, email=email, password=password)
                    UserProfile.objects.create(user=user, phone=phone)
                
                # Auto-login the user after successful registration
                user = authenticate(request, username=username, password=password)
                if user:
                    login(request, user)
                    request.session['user_id'] = user.id
                    request.session['username'] = username
                    return redirect('dashboard')
                else:
                    messages.success(request, 'Registration successful. Please log in.')
                    return redirect('login')
        except Exception as e:
            messages.error(request, f'An error occurred during registration: {str(e)}')
    
    return render(request, 'register.html')

def transactions_view(request):
    if 'username' in request.session:
        user_id = request.session['user_id']
        username = request.session['username']
        token = request.session.get('api_token')
        
        page = int(request.GET.get('page', 1))
        per_page = 10
        
        search_term = request.GET.get('search_term', '')
        start_date = request.GET.get('start_date', '')
        end_date = request.GET.get('end_date', '')
        transaction_type = request.GET.get('transaction_type', '')
        
        try:
            # Try to get transactions from API
            headers = {'Authorization': f'Bearer {token}'} if token else {}
            params = {
                'user_id': user_id,
                'page': page,
                'per_page': per_page,
                'search_term': search_term,
                'start_date': start_date,
                'end_date': end_date,
                'transaction_type': transaction_type
            }
            
            response = requests.get(f"{API_URL}/transactions", headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                return render(request, 'transaction.html', {
                    'username': username,
                    'page_obj': data['transactions'],
                    'page': page,
                    'total_pages': data['total_pages'],
                    'search_term': search_term,
                    'start_date': start_date,
                    'end_date': end_date,
                    'transaction_type': transaction_type,
                    'api_status': 'connected'
                })
            else:
                # API request failed, fall back to direct database access
                transactions = Transaction.objects.filter(user_id=user_id)
                
                if search_term:
                    transactions = transactions.filter(category__icontains=search_term) | transactions.filter(description__icontains=search_term)
                if start_date:
                    transactions = transactions.filter(date__gte=start_date)
                if end_date:
                    transactions = transactions.filter(date__lte=end_date)
                if transaction_type:
                    transactions = transactions.filter(transaction_type=transaction_type)
                
                from django.core.paginator import Paginator
                paginator = Paginator(transactions, per_page)
                page_obj = paginator.get_page(page)
                
                return render(request, 'transaction.html', {
                    'username': username,
                    'page_obj': page_obj,
                    'search_term': search_term,
                    'start_date': start_date,
                    'end_date': end_date,
                    'transaction_type': transaction_type,
                    'api_status': 'disconnected'
                })
        except requests.exceptions.RequestException:
            # API is down, fall back to direct database access
            transactions = Transaction.objects.filter(user_id=user_id)
            
            if search_term:
                transactions = transactions.filter(category__icontains=search_term) | transactions.filter(description__icontains=search_term)
            if start_date:
                transactions = transactions.filter(date__gte=start_date)
            if end_date:
                transactions = transactions.filter(date__lte=end_date)
            if transaction_type:
                transactions = transactions.filter(transaction_type=transaction_type)
            
            from django.core.paginator import Paginator
            paginator = Paginator(transactions, per_page)
            page_obj = paginator.get_page(page)
            
            return render(request, 'transaction.html', {
                'username': username,
                'page_obj': page_obj,
                'search_term': search_term,
                'start_date': start_date,
                'end_date': end_date,
                'transaction_type': transaction_type,
                'api_status': 'disconnected'
            })
    
    return redirect('login')

def edit_transaction(request, transaction_id):
    if 'username' not in request.session:
        return redirect('login')
    
    user_id = request.session['user_id']
    token = request.session.get('api_token')
    
    try:
        # Try to get transaction from API
        headers = {'Authorization': f'Bearer {token}'} if token else {}
        response = requests.get(f"{API_URL}/transactions/{transaction_id}", headers=headers)
        
        if response.status_code == 200:
            transaction = response.json()
        else:
            # API request failed, fall back to direct database access
            transaction = Transaction.objects.get(id=transaction_id)
    except requests.exceptions.RequestException:
        # API is down, fall back to direct database access
        transaction = Transaction.objects.get(id=transaction_id)

    if request.method == 'POST':
        date = request.POST.get('date')
        category = request.POST.get('category')
        amount = request.POST.get('amount')
        payment_method = request.POST.get('payment_method')
        description = request.POST.get('notes')
        transaction_type = request.POST.get('transaction_type')
        
        try:
            # Try to update via API
            headers = {'Authorization': f'Bearer {token}'} if token else {}
            data = {
                'user_id': user_id,
                'date': date,
                'category': category,
                'amount': amount,
                'payment_method': payment_method,
                'description': description,
                'transaction_type': transaction_type
            }
            
            response = requests.put(f"{API_URL}/transactions/{transaction_id}", headers=headers, json=data)
            
            if response.status_code == 200:
                messages.success(request, 'Transaction updated successfully.')
                return redirect('transactions')
            else:
                # API request failed, fall back to direct database update
                from django.db import transaction as db_transaction
                
                # Use transaction to prevent database locking
                with db_transaction.atomic():
                    transaction_obj = Transaction.objects.get(id=transaction_id)
                    transaction_obj.date = date
                    transaction_obj.category = category
                    transaction_obj.amount = amount
                    transaction_obj.payment_method = payment_method
                    transaction_obj.description = description
                    transaction_obj.transaction_type = transaction_type
                    transaction_obj.save()
                
                messages.success(request, 'Transaction updated successfully.')
                return redirect('transactions')
        except requests.exceptions.RequestException:
            # API is down, fall back to direct database update
            from django.db import transaction as db_transaction
            
            # Use transaction to prevent database locking
            with db_transaction.atomic():
                transaction_obj = Transaction.objects.get(id=transaction_id)
                transaction_obj.date = date
                transaction_obj.category = category
                transaction_obj.amount = amount
                transaction_obj.payment_method = payment_method
                transaction_obj.description = description
                transaction_obj.transaction_type = transaction_type
                transaction_obj.save()
            
            messages.success(request, 'Transaction updated successfully.')
            return redirect('transactions')

    categories = [
        "Entertainment",
        "Food",
        "Utilities",
        "Education",
        "Travel expenses",
        "Gifts",
        "Rent",
        "Subscriptions"
    ]   

    return render(request, 'edit_transaction.html', {
        'transaction': transaction,
        'categories': categories
    })

def add_transaction(request):
    if request.method == 'POST' and 'username' in request.session:
        user_id = request.session['user_id']
        token = request.session.get('api_token')
        
        date = request.POST.get('date')
        category = request.POST.get('category')
        amount = request.POST.get('amount')
        payment_method = request.POST.get('payment_method')
        description = request.POST.get('notes')
        transaction_type = request.POST.get('transaction_type')

        if all([date, category, amount, payment_method, transaction_type]):
            try:
                # Try to add transaction via API
                headers = {'Authorization': f'Bearer {token}'} if token else {}
                data = {
                    'user_id': user_id,
                    'date': date,
                    'category': category,
                    'amount': amount,
                    'payment_method': payment_method,
                    'description': description,
                    'transaction_type': transaction_type
                }
                
                response = requests.post(f"{API_URL}/transactions", headers=headers, json=data)
                
                if response.status_code == 201:
                    return redirect('transactions')
                else:
                    # API request failed, fall back to direct database insertion
                    from django.db import transaction
                    
                    # Use transaction to prevent database locking
                    with transaction.atomic():
                        Transaction.objects.create(
                            user_id=user_id,
                            date=date,
                            category=category,
                            amount=amount,
                            payment_method=payment_method,
                            description=description,
                            transaction_type=transaction_type
                        )
                    return redirect('transactions')
            except requests.exceptions.RequestException:
                # API is down, fall back to direct database insertion
                from django.db import transaction
                
                # Use transaction to prevent database locking
                with transaction.atomic():
                    Transaction.objects.create(
                        user_id=user_id,
                        date=date,
                        category=category,
                        amount=amount,
                        payment_method=payment_method,
                        description=description,
                        transaction_type=transaction_type
                    )
                return redirect('transactions')
        else:
            messages.error(request, 'Please fill all required fields.')
            return redirect('transactions')

    return redirect('login')

def delete_transaction(request, transaction_id):
    if request.method == 'POST' and 'username' in request.session:
        token = request.session.get('api_token')
        
        try:
            # Try to delete via API
            headers = {'Authorization': f'Bearer {token}'} if token else {}
            response = requests.delete(f"{API_URL}/transactions/{transaction_id}", headers=headers)
            
            if response.status_code != 204:
                # API request failed, fall back to direct database deletion
                from django.db import transaction
                
                # Use transaction to prevent database locking
                with transaction.atomic():
                    Transaction.objects.filter(id=transaction_id).delete()
        except requests.exceptions.RequestException:
            # API is down, fall back to direct database deletion
            from django.db import transaction
            
            # Use transaction to prevent database locking
            with transaction.atomic():
                    Transaction.objects.filter(id=transaction_id).delete()
        
        messages.success(request, 'Transaction deleted successfully.')
    
    return redirect('transactions')

def daily_spending_data(request):
    if 'username' in request.session:
        user_id = request.session['user_id']
        token = request.session.get('api_token')
        
        try:
            # Try to get data from API
            headers = {'Authorization': f'Bearer {token}'} if token else {}
            response = requests.get(f"{API_URL}/statistics/daily", headers=headers, params={'user_id': user_id})
            
            if response.status_code == 200:
                return JsonResponse(response.json())
            else:
                # API request failed, fall back to direct database access
                data = (
                    Transaction.objects.filter(user_id=user_id)
                    .values('date')
                    .annotate(total=models.Sum('amount'))
                    .order_by('date')
                )
                labels = [d['date'] for d in data]
                amounts = [d['total'] for d in data]
                return JsonResponse({'labels': labels, 'amounts': amounts})
        except requests.exceptions.RequestException:
            # API is down, fall back to direct database access
            data = (
                Transaction.objects.filter(user_id=user_id)
                .values('date')
                .annotate(total=models.Sum('amount'))
                .order_by('date')
            )
            labels = [d['date'] for d in data]
            amounts = [d['total'] for d in data]
            return JsonResponse({'labels': labels, 'amounts': amounts})
    
    return redirect('login')

def monthly_spending_data(request):
    if 'username' in request.session:
        user_id = request.session['user_id']
        token = request.session.get('api_token')
        
        try:
            # Try to get data from API
            headers = {'Authorization': f'Bearer {token}'} if token else {}
            response = requests.get(f"{API_URL}/statistics/monthly", headers=headers, params={'user_id': user_id})
            
            if response.status_code == 200:
                return JsonResponse(response.json())
            else:
                # API request failed, fall back to direct database access
                transactions = Transaction.objects.filter(user_id=user_id)
                monthly_data = {}

                for t in transactions:
                    key = t.date.strftime('%Y-%m')
                    monthly_data[key] = monthly_data.get(key, 0) + t.amount

                labels = [datetime.strptime(k, '%Y-%m').strftime('%b %Y') for k in monthly_data.keys()]
                amounts = list(monthly_data.values())
                return JsonResponse({'labels': labels, 'amounts': amounts})
        except requests.exceptions.RequestException:
            # API is down, fall back to direct database access
            transactions = Transaction.objects.filter(user_id=user_id)
            monthly_data = {}

            for t in transactions:
                key = t.date.strftime('%Y-%m')
                monthly_data[key] = monthly_data.get(key, 0) + t.amount

            labels = [datetime.strptime(k, '%Y-%m').strftime('%b %Y') for k in monthly_data.keys()]
            amounts = list(monthly_data.values())
            return JsonResponse({'labels': labels, 'amounts': amounts})
    
    return redirect('login')

def statistics(request):
    if 'user_id' in request.session:
        user_id = request.session['user_id']
        token = request.session.get('api_token')
        
        try:
            # Try to get statistics from API
            headers = {'Authorization': f'Bearer {token}'} if token else {}
            response = requests.get(f"{API_URL}/statistics", headers=headers, params={'user_id': user_id})
            
            if response.status_code == 200:
                data = response.json()
                return render(request, 'statistics.html', {
                    'total_expenses': data['total_expenses'],
                    'total_income': data['total_income'],
                    'expense_by_category': data['expense_by_category'],
                    'income_by_category': data['income_by_category'],
                    'top_spending_categories': data['top_spending_categories'],
                    'top_income_categories': data['top_income_categories'],
                    'api_status': 'connected'
                })
            else:
                # API request failed, fall back to direct database access
                transactions = Transaction.objects.filter(user_id=user_id)

                expenses = transactions.filter(transaction_type='Expense')
                income = transactions.filter(transaction_type='Income')

                total_expenses = sum(t.amount for t in expenses)
                total_income = sum(t.amount for t in income)

                expense_by_category = {}
                for t in expenses:
                    expense_by_category[t.category] = expense_by_category.get(t.category, 0) + t.amount

                income_by_category = {}
                for t in income:
                    income_by_category[t.category] = income_by_category.get(t.category, 0) + t.amount

                top_spending_categories = dict(sorted(expense_by_category.items(), key=lambda x: x[1], reverse=True)[:5])
                top_income_categories = dict(sorted(income_by_category.items(), key=lambda x: x[1], reverse=True)[:5])

                return render(request, 'statistics.html', {
                    'total_expenses': total_expenses,
                    'total_income': total_income,
                    'expense_by_category': expense_by_category,
                    'income_by_category': income_by_category,
                    'top_spending_categories': top_spending_categories,
                    'top_income_categories': top_income_categories,
                    'api_status': 'disconnected'
                })
        except requests.exceptions.RequestException:
            # API is down, fall back to direct database access
            transactions = Transaction.objects.filter(user_id=user_id)

            expenses = transactions.filter(transaction_type='Expense')
            income = transactions.filter(transaction_type='Income')

            total_expenses = sum(t.amount for t in expenses)
            total_income = sum(t.amount for t in income)

            expense_by_category = {}
            for t in expenses:
                expense_by_category[t.category] = expense_by_category.get(t.category, 0) + t.amount

            income_by_category = {}
            for t in income:
                income_by_category[t.category] = income_by_category.get(t.category, 0) + t.amount

            top_spending_categories = dict(sorted(expense_by_category.items(), key=lambda x: x[1], reverse=True)[:5])
            top_income_categories = dict(sorted(income_by_category.items(), key=lambda x: x[1], reverse=True)[:5])

            return render(request, 'statistics.html', {
                'total_expenses': total_expenses,
                'total_income': total_income,
                'expense_by_category': expense_by_category,
                'income_by_category': income_by_category,
                'top_spending_categories': top_spending_categories,
                'top_income_categories': top_income_categories,
                'api_status': 'disconnected'
            })

    return redirect('login')

def about(request):
    return render(request, 'about.html')

def features(request):
    return render(request, 'features.html')

def learn_more(request):
    return render(request, 'learn_more.html')

def discover_more(request):
    return render(request, 'discover_more.html')

def explore_more(request):
    return render(request, 'explore_more.html')

# Add the about_us view function
def about_us(request):
    return render(request, 'about_us.html')

# Modify the view_trends function to allow access without login
def view_trends(request):
    # Remove login check to make it accessible without authentication
    user_id = request.session.get('user_id')
    username = request.session.get('username')
    token = request.session.get('api_token')
    
    try:
        # If user is logged in, try to get data from API
        if user_id:
            headers = {'Authorization': f'Bearer {token}'} if token else {}
            response = requests.get(f"{API_URL}/statistics/trends", headers=headers, params={'user_id': user_id})
            
            if response.status_code == 200:
                data = response.json()
                return render(request, 'view_trends.html', {
                    'username': username,
                    'trends_data': data,
                    'api_status': 'connected'
                })
            else:
                # API request failed, fall back to direct database access
                transactions = Transaction.objects.filter(user_id=user_id)
                
                # Calculate monthly trends
                monthly_data = {}
                for t in transactions:
                    key = t.date.strftime('%Y-%m')
                    if key not in monthly_data:
                        monthly_data[key] = {'income': 0, 'expense': 0}
                    
                    if t.transaction_type == 'Income':
                        monthly_data[key]['income'] += t.amount
                    else:
                        monthly_data[key]['expense'] += t.amount
                
                # Calculate category trends
                category_data = {}
                for t in transactions:
                    if t.category not in category_data:
                        category_data[t.category] = 0
                    category_data[t.category] += t.amount
                
                # Calculate payment method trends
                payment_data = {}
                for t in transactions:
                    if t.payment_method not in payment_data:
                        payment_data[t.payment_method] = 0
                    payment_data[t.payment_method] += t.amount
                
                # Format data for template
                monthly_labels = sorted(monthly_data.keys())
                monthly_income = [monthly_data[k]['income'] for k in monthly_labels]
                monthly_expense = [monthly_data[k]['expense'] for k in monthly_labels]
                monthly_labels = [datetime.strptime(k, '%Y-%m').strftime('%b %Y') for k in monthly_labels]
                
                return render(request, 'view_trends.html', {
                    'username': username,
                    'monthly_labels': monthly_labels,
                    'monthly_income': monthly_income,
                    'monthly_expense': monthly_expense,
                    'category_data': category_data,
                    'payment_data': payment_data,
                    'api_status': 'disconnected'
                })
        else:
            # For non-logged in users, show sample data
            monthly_labels = ['Jan 2025', 'Feb 2025', 'Mar 2025', 'Apr 2025', 'May 2025']
            monthly_income = [5000, 5200, 5300, 5100, 5400]
            monthly_expense = [3800, 4100, 3900, 4000, 4200]
            
            category_data = {
                'Food': 1500,
                'Entertainment': 800,
                'Utilities': 1200,
                'Education': 900,
                'Travel': 600
            }
            
            payment_data = {
                'Cash': 2000,
                'UPI': 3000,
                'Credit Card': 1500,
                'Debit Card': 1000
            }
            
            return render(request, 'view_trends.html', {
                'username': None,
                'monthly_labels': monthly_labels,
                'monthly_income': monthly_income,
                'monthly_expense': monthly_expense,
                'category_data': category_data,
                'payment_data': payment_data,
                'api_status': 'sample'
            })
    except requests.exceptions.RequestException:
        # If user is logged in but API is down, fall back to direct database access
        if user_id:
            transactions = Transaction.objects.filter(user_id=user_id)
            
            # Calculate monthly trends
            monthly_data = {}
            for t in transactions:
                key = t.date.strftime('%Y-%m')
                if key not in monthly_data:
                    monthly_data[key] = {'income': 0, 'expense': 0}
                
                if t.transaction_type == 'Income':
                    monthly_data[key]['income'] += t.amount
                else:
                    monthly_data[key]['expense'] += t.amount
            
            # Calculate category trends
            category_data = {}
            for t in transactions:
                if t.category not in category_data:
                    category_data[t.category] = 0
                category_data[t.category] += t.amount
            
            # Calculate payment method trends
            payment_data = {}
            for t in transactions:
                if t.payment_method not in payment_data:
                    payment_data[t.payment_method] = 0
                payment_data[t.payment_method] += t.amount
            
            # Format data for template
            monthly_labels = sorted(monthly_data.keys())
            monthly_income = [monthly_data[k]['income'] for k in monthly_labels]
            monthly_expense = [monthly_data[k]['expense'] for k in monthly_labels]
            monthly_labels = [datetime.strptime(k, '%Y-%m').strftime('%b %Y') for k in monthly_labels]
            
            return render(request, 'view_trends.html', {
                'username': username,
                'monthly_labels': monthly_labels,
                'monthly_income': monthly_income,
                'monthly_expense': monthly_expense,
                'category_data': category_data,
                'payment_data': payment_data,
                'api_status': 'disconnected'
            })
        else:
            # For non-logged in users, show sample data
            monthly_labels = ['Jan 2025', 'Feb 2025', 'Mar 2025', 'Apr 2025', 'May 2025']
            monthly_income = [5000, 5200, 5300, 5100, 5400]
            monthly_expense = [3800, 4100, 3900, 4000, 4200]
            
            category_data = {
                'Food': 1500,
                'Entertainment': 800,
                'Utilities': 1200,
                'Education': 900,
                'Travel': 600
            }
            
            payment_data = {
                'Cash': 2000,
                'UPI': 3000,
                'Credit Card': 1500,
                'Debit Card': 1000
            }
            
            return render(request, 'view_trends.html', {
                'username': None,
                'monthly_labels': monthly_labels,
                'monthly_income': monthly_income,
                'monthly_expense': monthly_expense,
                'category_data': category_data,
                'payment_data': payment_data,
                'api_status': 'sample'
            })

# Add a new view function for recent transactions
def recent_transactions(request):
    if 'username' in request.session:
        user_id = request.session['user_id']
        
        try:
            # Get the latest 10 transactions
            transactions = Transaction.objects.filter(user_id=user_id).order_by('-date')[:10]
            data = []
            
            for t in transactions:
                data.append({
                    'id': t.id,
                    'date': t.date.strftime('%Y-%m-%d'),
                    'category': t.category,
                    'description': t.description or '',
                    'amount': t.amount,
                    'type': t.transaction_type
                })
            
            return JsonResponse({'transactions': data})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Not authenticated'}, status=401)

def income_expense_data(request):
    if 'username' in request.session:
        user_id = request.session['user_id']
        period = request.GET.get('period', 'monthly')
        
        try:
            # Get transactions for the last 6 months or 12 weeks
            end_date = timezone.now().date()
            
            if period == 'monthly':
                start_date = end_date - timedelta(days=180)  # 6 months
                # Group by month
                income_data = Transaction.objects.filter(
                    user_id=user_id,
                    transaction_type='Income',
                    date__gte=start_date,
                    date__lte=end_date
                ).annotate(
                    month=TruncMonth('date')
                ).values('month').annotate(
                    total=Sum('amount')
                ).order_by('month')
                
                expense_data = Transaction.objects.filter(
                    user_id=user_id,
                    transaction_type='Expense',
                    date__gte=start_date,
                    date__lte=end_date
                ).annotate(
                    month=TruncMonth('date')
                ).values('month').annotate(
                    total=Sum('amount')
                ).order_by('month')
                
                # Create a list of all months in the range
                months = []
                current_date = start_date.replace(day=1)
                while current_date <= end_date:
                    months.append(current_date)
                    # Move to next month
                    if current_date.month == 12:
                        current_date = current_date.replace(year=current_date.year + 1, month=1)
                    else:
                        current_date = current_date.replace(month=current_date.month + 1)
                
                # Format the data
                labels = [d.strftime('%b %Y') for d in months]
                income_values = [0] * len(months)
                expense_values = [0] * len(months)
                
                # Fill in income data
                for item in income_data:
                    month_idx = months.index(item['month'].date().replace(day=1))
                    income_values[month_idx] = float(item['total'])
                
                # Fill in expense data
                for item in expense_data:
                    month_idx = months.index(item['month'].date().replace(day=1))
                    expense_values[month_idx] = float(item['total'])
                
            else:  # weekly
                start_date = end_date - timedelta(days=84)  # 12 weeks
                # Group by week
                income_data = Transaction.objects.filter(
                    user_id=user_id,
                    transaction_type='Income',
                    date__gte=start_date,
                    date__lte=end_date
                ).annotate(
                    week=TruncWeek('date')
                ).values('week').annotate(
                    total=Sum('amount')
                ).order_by('week')
                
                expense_data = Transaction.objects.filter(
                    user_id=user_id,
                    transaction_type='Expense',
                    date__gte=start_date,
                    date__lte=end_date
                ).annotate(
                    week=TruncWeek('date')
                ).values('week').annotate(
                    total=Sum('amount')
                ).order_by('week')
                
                # Create a list of all weeks in the range
                weeks = []
                current_date = start_date - timedelta(days=start_date.weekday())  # Start from Monday
                while current_date <= end_date:
                    weeks.append(current_date)
                    current_date += timedelta(days=7)
                
                # Format the data
                labels = [f"{d.strftime('%d %b')}-{(d + timedelta(days=6)).strftime('%d %b')}" for d in weeks]
                income_values = [0] * len(weeks)
                expense_values = [0] * len(weeks)
                
                # Fill in income data
                for item in income_data:
                    week_date = item['week'].date()
                    week_start = week_date - timedelta(days=week_date.weekday())
                    if week_start in weeks:
                        week_idx = weeks.index(week_start)
                        income_values[week_idx] = float(item['total'])
                
                # Fill in expense data
                for item in expense_data:
                    week_date = item['week'].date()
                    week_start = week_date - timedelta(days=week_date.weekday())
                    if week_start in weeks:
                        week_idx = weeks.index(week_start)
                        expense_values[week_idx] = float(item['total'])
            
            # If no data, provide sample data
            if not labels:
                if period == 'monthly':
                    labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
                else:
                    labels = ['Week 1', 'Week 2', 'Week 3', 'Week 4', 'Week 5', 'Week 6']
                income_values = [5000, 5200, 5300, 5100, 5400, 5600]
                expense_values = [3800, 4100, 3900, 4000, 4200, 4300]
            
            return JsonResponse({
                'labels': labels,
                'income': income_values,
                'expense': expense_values
            })
            
        except Exception as e:
            # Return sample data on error
            if period == 'monthly':
                labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
            else:
                labels = ['Week 1', 'Week 2', 'Week 3', 'Week 4', 'Week 5', 'Week 6']
            income_values = [5000, 5200, 5300, 5100, 5400, 5600]
            expense_values = [3800, 4100, 3900, 4000, 4200, 4300]
            
            return JsonResponse({
                'labels': labels,
                'income': income_values,
                'expense': expense_values,
                'error': str(e)
            })
    
    # Return sample data for non-authenticated users
    if period == 'monthly':
        labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
    else:
        labels = ['Week 1', 'Week 2', 'Week 3', 'Week 4', 'Week 5', 'Week 6']
    income_values = [5000, 5200, 5300, 5100, 5400, 5600]
    expense_values = [3800, 4100, 3900, 4000, 4200, 4300]
    
    return JsonResponse({
        'labels': labels,
        'income': income_values,
        'expense': expense_values,
        'status': 'sample'
    })

# Add this new view function for category data
def category_data(request):
    if 'username' in request.session:
        user_id = request.session['user_id']
        period = request.GET.get('period', 'monthly')
        
        try:
            # Get transactions for the selected period
            end_date = timezone.now().date()
            
            if period == 'monthly':
                start_date = end_date.replace(day=1)  # Start of current month
            else:  # weekly
                # Start of current week (Monday)
                start_date = end_date - timedelta(days=end_date.weekday())
            
            # Get expense transactions grouped by category
            category_data = Transaction.objects.filter(
                user_id=user_id,
                transaction_type='Expense',
                date__gte=start_date,
                date__lte=end_date
            ).values('category').annotate(
                total=Sum('amount')
            ).order_by('-total')
            
            if not category_data:
                return JsonResponse({
                    'labels': ['No Data Available'],
                    'values': [100]
                })
            
            # Calculate total expenses
            total_expenses = sum(item['total'] for item in category_data)
            
            # Format the data
            labels = [item['category'] for item in category_data]
            # Calculate percentage values
            values = [round((item['total'] / total_expenses) * 100, 1) for item in category_data]
            
            return JsonResponse({
                'labels': labels,
                'values': values
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Not authenticated'}, status=401)

# Add this new view function for payment method data
def payment_method_data(request):
    if 'username' in request.session:
        user_id = request.session['user_id']
        
        try:
            # Get all payment methods used by the user
            payment_methods = Transaction.objects.filter(
                user_id=user_id
            ).values('payment_method').distinct()
            
            result = []
            
            for method in payment_methods:
                method_name = method['payment_method']
                
                # Get total expense for this payment method
                expense = Transaction.objects.filter(
                    user_id=user_id,
                    payment_method=method_name,
                    transaction_type='Expense'
                ).aggregate(total=Sum('amount'))['total'] or 0
                
                # Get total income for this payment method
                income = Transaction.objects.filter(
                    user_id=user_id,
                    payment_method=method_name,
                    transaction_type='Income'
                ).aggregate(total=Sum('amount'))['total'] or 0
                
                # Get last transaction date
                last_transaction = Transaction.objects.filter(
                    user_id=user_id,
                    payment_method=method_name
                ).order_by('-date').first()
                
                last_date = None
                if last_transaction:
                    last_date = last_transaction.date.strftime('%Y-%m-%d')
                
                result.append({
                    'name': method_name,
                    'expense': expense,
                    'income': income,
                    'last_transaction_date': last_date
                })
            
            return JsonResponse({'payment_methods': result})
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Not authenticated'}, status=401)
