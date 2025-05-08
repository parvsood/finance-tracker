from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='sankalp_dashboard'),
    path('goals/', views.goals_list, name='goals_list'),
    path('goals/create/', views.create_goal, name='create_goal'),
    path('goals/<int:goal_id>/', views.goal_detail, name='goal_detail'),
    path('goals/<int:goal_id>/edit/', views.edit_goal, name='edit_goal'),
    path('goals/<int:goal_id>/delete/', views.delete_goal, name='delete_goal'),
    path('goals/<int:goal_id>/update-progress/', views.update_progress, name='update_progress'),
    
    path('journals/', views.journals_list, name='journals_list'),
    path('journals/create/<int:goal_id>/', views.create_journal, name='create_journal'),
    path('journals/<int:journal_id>/', views.journal_detail, name='journal_detail'),
    path('journals/<int:journal_id>/edit/', views.edit_journal, name='edit_journal'),
    path('journals/<int:journal_id>/delete/', views.delete_journal, name='delete_journal'),
    
    path('milestones/create/<int:goal_id>/', views.create_milestone, name='create_milestone'),
    path('milestones/<int:milestone_id>/toggle/', views.toggle_milestone, name='toggle_milestone'),
    path('milestones/<int:milestone_id>/delete/', views.delete_milestone, name='delete_milestone'),
    
    path('api/finance-data/', views.finance_data, name='finance_data'),
]
