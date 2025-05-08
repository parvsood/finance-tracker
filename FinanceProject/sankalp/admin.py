from django.contrib import admin
from .models import Goal, Journal, Milestone

@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'goal_type', 'target_date', 'status', 'progress_percentage')
    list_filter = ('goal_type', 'status', 'start_date')
    search_fields = ('title', 'description')

@admin.register(Journal)
class JournalAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'goal', 'created_at')
    list_filter = ('created_at', 'mood')
    search_fields = ('title', 'content')

@admin.register(Milestone)
class MilestoneAdmin(admin.ModelAdmin):
    list_display = ('title', 'goal', 'target_date', 'is_completed')
    list_filter = ('is_completed', 'target_date')
    search_fields = ('title', 'description')
