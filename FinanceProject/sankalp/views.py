from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from datetime import date, datetime, timedelta
import requests
import json
from django.db import transaction
from .models import Goal, Journal, Milestone
from .forms import GoalForm, JournalForm, MilestoneForm, ProgressUpdateForm
from financeapp.models import Transaction
from django.db.models import Sum
from django.contrib.auth.models import User

@login_required
def dashboard(request):
    if 'username' not in request.session:
        return redirect('login')
    
    user_id = request.session['user_id']
    user = User.objects.get(id=user_id)
    
    # Get all goals for the user
    goals = Goal.objects.filter(user=user)
    
    # Initialize counters to 0
    total_goals = 0
    completed_goals = 0
    in_progress_goals = 0
    
    # Only count if there are goals
    if goals.exists():
        total_goals = goals.count()
        completed_goals = goals.filter(status='COMPLETED').count()
        in_progress_goals = goals.filter(status='IN_PROGRESS').count()
    
    # Calculate completion rate
    completion_rate = 0
    if total_goals > 0:
        completion_rate = (completed_goals / total_goals) * 100
    
    # Get in-progress goals for display
    in_progress_goals_list = goals.filter(status='IN_PROGRESS').order_by('target_date')[:5]
    
    # Get upcoming goals (with closest deadlines)
    upcoming_goals = goals.filter(status__in=['NOT_STARTED', 'IN_PROGRESS']).order_by('target_date')[:5]
    
    # Get recent journal entries
    recent_journals = Journal.objects.filter(user=user).order_by('-created_at')[:4]
    
    # Get all goals for calendar
    all_goals = []
    for goal in goals:
        # Calculate days remaining
        if goal.target_date:
            today = timezone.now().date()
            days_remaining = (goal.target_date - today).days
            if days_remaining < 0:
                days_remaining = 0
        else:
            days_remaining = 0
            
        goal_data = {
            'id': goal.id,
            'title': goal.title,
            'target_date': goal.target_date,
            'goal_type': goal.goal_type,
            'days_remaining': days_remaining,
            'progress_percentage': goal.progress_percentage()
        }
        all_goals.append(goal_data)
    
    # Get transaction data for income vs expense chart
    current_month = timezone.now().month
    current_year = timezone.now().year
    
    # Get all transactions for the current month
    transactions = Transaction.objects.filter(
        user=user,
        date__month=current_month,
        date__year=current_year
    )
    
    # Calculate income and expenses
    income = transactions.filter(transaction_type='Income').aggregate(Sum('amount'))['amount__sum'] or 0
    expenses = transactions.filter(transaction_type='Expense').aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Prepare data for the chart
    income_vs_expense = [
        {'category': 'Income', 'amount': float(income)},
        {'category': 'Expense', 'amount': float(expenses)}
    ]
    
    context = {
        'total_goals': total_goals,
        'completed_goals': completed_goals,
        'in_progress_goals': in_progress_goals_list,
        'completion_rate': round(completion_rate, 1),
        'upcoming_goals': upcoming_goals,
        'recent_journals': recent_journals,
        'all_goals': all_goals,
        'income_vs_expense': income_vs_expense,
        'income': float(income),
        'expenses': float(expenses),
        'username': request.session.get('username', '')
    }
    
    return render(request, 'sankalp/dashboard.html', context)

@login_required
def goals_list(request):
    # Get filter parameters
    goal_type = request.GET.get('goal_type', '')
    status = request.GET.get('status', '')
    
    # Start with all user's goals
    goals = Goal.objects.filter(user=request.user)
    
    # Apply filters if provided
    if goal_type:
        goals = goals.filter(goal_type=goal_type)
    if status:
        goals = goals.filter(status=status)
    
    # Order by created date
    goals = goals.order_by('-created_at')
    
    return render(request, 'sankalp/goals_list.html', {
        'goals': goals,
        'username': request.session.get('username', '')
    })

@login_required
def create_goal(request):
    if request.method == 'POST':
        form = GoalForm(request.POST)
        if form.is_valid():
            # Use transaction to prevent database locking
            with transaction.atomic():
                goal = form.save(commit=False)
                goal.user = request.user
                goal.save()
            
            messages.success(request, 'Goal created successfully!')
            return redirect('goal_detail', goal_id=goal.id)
    else:
        form = GoalForm(initial={
            'start_date': date.today(),
            'target_date': date.today() + timedelta(days=90),  # Default 3 months
            'status': 'NOT_STARTED'
        })
    
    return render(request, 'sankalp/goal_form.html', {
        'form': form, 
        'title': 'Create New Goal',
        'username': request.session.get('username', '')
    })

@login_required
def goal_detail(request, goal_id):
    goal = get_object_or_404(Goal, id=goal_id, user=request.user)
    journals = Journal.objects.filter(goal=goal).order_by('-created_at')
    milestones = Milestone.objects.filter(goal=goal).order_by('target_date')
    
    # Get financial data related to this goal
    financial_data = get_financial_data(request, goal)
    
    context = {
        'goal': goal,
        'journals': journals,
        'milestones': milestones,
        'progress_form': ProgressUpdateForm(instance=goal),
        'milestone_form': MilestoneForm(),
        'financial_data': financial_data,
        'username': request.session.get('username', '')
    }
    
    return render(request, 'sankalp/goal_detail.html', context)

@login_required
def edit_goal(request, goal_id):
    goal = get_object_or_404(Goal, id=goal_id, user=request.user)
    
    if request.method == 'POST':
        form = GoalForm(request.POST, instance=goal)
        if form.is_valid():
            with transaction.atomic():
                form.save()
            messages.success(request, 'Goal updated successfully!')
            return redirect('goal_detail', goal_id=goal.id)
    else:
        form = GoalForm(instance=goal)
    
    return render(request, 'sankalp/goal_form.html', {
        'form': form, 
        'title': 'Edit Goal',
        'username': request.session.get('username', '')
    })

@login_required
def delete_goal(request, goal_id):
    goal = get_object_or_404(Goal, id=goal_id, user=request.user)
    
    if request.method == 'POST':
        with transaction.atomic():
            goal.delete()
        messages.success(request, 'Goal deleted successfully!')
        return redirect('goals_list')
    
    return render(request, 'sankalp/confirm_delete.html', {
        'object': goal, 
        'object_type': 'Goal',
        'username': request.session.get('username', '')
    })

@login_required
def update_progress(request, goal_id):
    goal = get_object_or_404(Goal, id=goal_id, user=request.user)
    
    if request.method == 'POST':
        form = ProgressUpdateForm(request.POST, instance=goal)
        if form.is_valid():
            with transaction.atomic():
                goal = form.save()
                
                # Check if goal is completed
                if goal.progress_percentage() >= 100 and goal.status != 'COMPLETED':
                    goal.status = 'COMPLETED'
                    goal.save()
                    messages.success(request, 'Congratulations! You have completed your goal!')
                else:
                    messages.success(request, 'Progress updated successfully!')
                
            return redirect('goal_detail', goal_id=goal.id)
    
    return redirect('goal_detail', goal_id=goal.id)

@login_required
def journals_list(request):
    journals = Journal.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'sankalp/journals_list.html', {
        'journals': journals,
        'username': request.session.get('username', '')
    })

@login_required
def create_journal(request, goal_id):
    goal = get_object_or_404(Goal, id=goal_id, user=request.user)
    
    if request.method == 'POST':
        form = JournalForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                journal = form.save(commit=False)
                journal.user = request.user
                journal.goal = goal
                journal.save()
            messages.success(request, 'Journal entry created successfully!')
            return redirect('goal_detail', goal_id=goal.id)
    else:
        form = JournalForm()
    
    return render(request, 'sankalp/journal_form.html', {
        'form': form, 
        'title': 'Create Journal Entry',
        'goal': goal,
        'username': request.session.get('username', '')
    })

@login_required
def journal_detail(request, journal_id):
    journal = get_object_or_404(Journal, id=journal_id, user=request.user)
    return render(request, 'sankalp/journal_detail.html', {
        'journal': journal,
        'username': request.session.get('username', '')
    })

@login_required
def edit_journal(request, journal_id):
    journal = get_object_or_404(Journal, id=journal_id, user=request.user)
    
    if request.method == 'POST':
        form = JournalForm(request.POST, instance=journal)
        if form.is_valid():
            with transaction.atomic():
                form.save()
            messages.success(request, 'Journal entry updated successfully!')
            return redirect('journal_detail', journal_id=journal.id)
    else:
        form = JournalForm(instance=journal)
    
    return render(request, 'sankalp/journal_form.html', {
        'form': form, 
        'title': 'Edit Journal Entry',
        'goal': journal.goal,
        'username': request.session.get('username', '')
    })

@login_required
def delete_journal(request, journal_id):
    journal = get_object_or_404(Journal, id=journal_id, user=request.user)
    goal_id = journal.goal.id
    
    if request.method == 'POST':
        with transaction.atomic():
            journal.delete()
        messages.success(request, 'Journal entry deleted successfully!')
        return redirect('goal_detail', goal_id=goal_id)
    
    return render(request, 'sankalp/confirm_delete.html', {
        'object': journal, 
        'object_type': 'Journal Entry',
        'username': request.session.get('username', '')
    })

@login_required
def create_milestone(request, goal_id):
    goal = get_object_or_404(Goal, id=goal_id, user=request.user)
    
    if request.method == 'POST':
        form = MilestoneForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                milestone = form.save(commit=False)
                milestone.goal = goal
                milestone.save()
            messages.success(request, 'Milestone added successfully!')
    
    return redirect('goal_detail', goal_id=goal.id)

@login_required
def toggle_milestone(request, milestone_id):
    milestone = get_object_or_404(Milestone, id=milestone_id, goal__user=request.user)
    
    with transaction.atomic():
        milestone.is_completed = not milestone.is_completed
        if milestone.is_completed:
            milestone.completed_date = timezone.now().date()
        else:
            milestone.completed_date = None
        milestone.save()
        
        # Update goal progress based on milestones if applicable
        goal = milestone.goal
        if goal.goal_type == 'PERSONAL' or goal.goal_type == 'CAREER':
            total_milestones = Milestone.objects.filter(goal=goal).count()
            completed_milestones = Milestone.objects.filter(goal=goal, is_completed=True).count()
            
            if total_milestones > 0:
                # For non-financial goals, use milestones to track progress
                progress_percentage = (completed_milestones / total_milestones) * 100
                # Set current_amount based on percentage of target_amount
                if goal.target_amount:
                    goal.current_amount = (progress_percentage / 100) * goal.target_amount
                    goal.save()
    
    return redirect('goal_detail', goal_id=milestone.goal.id)

@login_required
def delete_milestone(request, milestone_id):
    milestone = get_object_or_404(Milestone, id=milestone_id, goal__user=request.user)
    goal_id = milestone.goal.id
    
    with transaction.atomic():
        milestone.delete()
    messages.success(request, 'Milestone deleted successfully!')
    
    return redirect('goal_detail', goal_id=goal_id)

@login_required
def finance_data(request):
    """
    API endpoint to fetch financial data from the Flask API
    """
    try:
        # Call the Flask API
        api_url = "http://localhost:5000/api/finance-data"
        response = requests.get(
            api_url, 
            params={'user_id': request.user.id},
            headers={'Authorization': f'Bearer {request.session.get("auth_token", "")}'}
        )
        
        if response.status_code == 200:
            return JsonResponse(response.json())
        else:
            # Fall back to direct database access
            return get_finance_data_from_db(request.user.id)
    except Exception:
        # Fall back to direct database access
        return get_finance_data_from_db(request.user.id)

def get_finance_data_from_db(user_id):
    """Helper function to get finance data directly from the database"""
    try:
        with transaction.atomic():
            # Get transactions for the user
            transactions = Transaction.objects.filter(user_id=user_id)
            
            # Calculate monthly spending
            monthly_data = {}
            for t in transactions:
                if not t.date:
                    continue
                    
                month_key = t.date.strftime('%Y-%m')
                if month_key not in monthly_data:
                    monthly_data[month_key] = 0
                monthly_data[month_key] += t.amount
            
            # Format data for response
            months = [datetime.strptime(k, '%Y-%m').strftime('%b %Y') for k in sorted(monthly_data.keys())] if monthly_data else []
            spending = [monthly_data[k] for k in sorted(monthly_data.keys())] if monthly_data else []
            
            # Calculate averages
            avg_monthly_spending = sum(spending) / len(spending) if spending else 0
            
            data = {
                'months': months,
                'spending': spending,
                'avg_monthly_spending': avg_monthly_spending,
                'monthly_savings_potential': 0,  # Placeholder
                'estimated_completion_months': 0  # Placeholder
            }
            
            return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def get_financial_data(request, goal):
    """
    Helper function to get relevant financial data for a goal
    """
    try:
        # Try to get data from Flask API
        api_url = "http://localhost:5000/api/finance-data"
        response = requests.get(
            api_url, 
            params={'user_id': request.user.id, 'goal_type': goal.goal_type},
            headers={'Authorization': f'Bearer {request.session.get("auth_token", "")}'}
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            # Fall back to direct database calculation
            return calculate_financial_data(request.user.id, goal)
    except Exception:
        # Fall back to direct database calculation
        return calculate_financial_data(request.user.id, goal)

def calculate_financial_data(user_id, goal):
    """Calculate financial data directly from the database"""
    try:
        with transaction.atomic():
            # Get transactions for the user
            transactions = Transaction.objects.filter(user_id=user_id)
            
            # Calculate monthly spending
            monthly_data = {}
            for t in transactions:
                if not t.date:
                    continue
                    
                month_key = t.date.strftime('%Y-%m')
                if month_key not in monthly_data:
                    monthly_data[month_key] = 0
                
                # For expenses, add to the monthly total
                if t.transaction_type == 'Expense':
                    monthly_data[month_key] += t.amount
            
            # Format data for response
            months = [datetime.strptime(k, '%Y-%m').strftime('%b %Y') for k in sorted(monthly_data.keys())] if monthly_data else []
            spending = [monthly_data[k] for k in sorted(monthly_data.keys())] if monthly_data else []
            
            # Calculate averages
            avg_monthly_spending = sum(spending) / len(spending) if spending else 0
            
            # Calculate monthly savings potential (income - expenses)
            income_transactions = transactions.filter(transaction_type='Income')
            expense_transactions = transactions.filter(transaction_type='Expense')
            
            total_income = sum(t.amount for t in income_transactions)
            total_expenses = sum(t.amount for t in expense_transactions)
            
            # Calculate average monthly income and expenses
            num_months = len(monthly_data) or 1  # Avoid division by zero
            avg_monthly_income = total_income / num_months
            avg_monthly_expenses = total_expenses / num_months
            
            monthly_savings_potential = avg_monthly_income - avg_monthly_expenses
            
            # Estimate months to complete goal
            if goal.target_amount and monthly_savings_potential > 0:
                remaining_amount = goal.target_amount - goal.current_amount
                estimated_completion_months = round(remaining_amount / monthly_savings_potential)
            else:
                estimated_completion_months = 0
            
            return {
                'months': months,
                'spending': spending,
                'avg_monthly_spending': avg_monthly_spending,
                'monthly_savings_potential': monthly_savings_potential,
                'estimated_completion_months': estimated_completion_months
            }
    except Exception as e:
        # Return empty data on error
        return {
            'error': str(e),
            'months': [],
            'spending': [],
            'avg_monthly_spending': 0,
            'monthly_savings_potential': 0,
            'estimated_completion_months': 0
        }
