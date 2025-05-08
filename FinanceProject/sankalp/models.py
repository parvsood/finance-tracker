from django.db import models
from django.contrib.auth.models import User
from datetime import date

class Goal(models.Model):
    GOAL_TYPES = [
        ('FINANCIAL', 'Financial'),
        ('PERSONAL', 'Personal'),
        ('CAREER', 'Career'),
        ('HEALTH', 'Health'),
        ('OTHER', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('NOT_STARTED', 'Not Started'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('ABANDONED', 'Abandoned'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField()
    goal_type = models.CharField(max_length=20, choices=GOAL_TYPES)
    target_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    current_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    start_date = models.DateField()
    target_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='NOT_STARTED')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def progress_percentage(self):
        if not self.target_amount or self.target_amount == 0:
            # For non-financial goals, calculate based on milestones if available
            milestones = self.milestones.all()
            if milestones.exists():
                completed = milestones.filter(is_completed=True).count()
                total = milestones.count()
                return (completed / total) * 100 if total > 0 else 0
            return 0
        progress = (self.current_amount / self.target_amount) * 100
        return min(100, max(0, progress))
    
    def days_remaining(self):
        today = date.today()
        if today > self.target_date:
            return 0
        return (self.target_date - today).days
    
    def is_on_track(self):
        if self.status != 'IN_PROGRESS':
            return None
            
        # Calculate expected progress based on time elapsed
        total_days = (self.target_date - self.start_date).days
        days_passed = (date.today() - self.start_date).days
        
        if total_days <= 0 or days_passed < 0:
            return None
            
        expected_progress = (days_passed / total_days) * 100
        actual_progress = self.progress_percentage()
        
        # Return True if actual progress is at least 90% of expected progress
        return actual_progress >= (expected_progress * 0.9)
    
    def __str__(self):
        return self.title

class Journal(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    goal = models.ForeignKey(Goal, on_delete=models.CASCADE, related_name='journals')
    title = models.CharField(max_length=200)
    content = models.TextField()
    mood = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.title

class Milestone(models.Model):
    goal = models.ForeignKey(Goal, on_delete=models.CASCADE, related_name='milestones')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    target_date = models.DateField()
    is_completed = models.BooleanField(default=False)
    completed_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.title
