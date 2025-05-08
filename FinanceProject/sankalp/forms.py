from django import forms
from .models import Goal, Journal, Milestone

class GoalForm(forms.ModelForm):
    class Meta:
        model = Goal
        fields = ['title', 'description', 'goal_type', 'target_amount', 'start_date', 'target_date', 'status']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'target_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 4}),
        }

class JournalForm(forms.ModelForm):
    class Meta:
        model = Journal
        fields = ['title', 'content', 'mood']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 6}),
        }

class MilestoneForm(forms.ModelForm):
    class Meta:
        model = Milestone
        fields = ['title', 'description', 'target_date']
        widgets = {
            'target_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class ProgressUpdateForm(forms.ModelForm):
    class Meta:
        model = Goal
        fields = ['current_amount', 'status']
