from django.urls import path
from . import views

app_name = 'aid_management'

urlpatterns = [
    # =================================================================
    # 1. واجهات الطالب (Student Portal)
    # =================================================================
    path('applications/', 
        views.StudentApplicationListView.as_view(), 
        name='student_application_list'),
    
    path('applications/new/', 
        views.StudentApplicationCreateView.as_view(), 
        name='student_application_create'),
    
    path('applications/<uuid:pk>/', 
        views.StudentApplicationDetailView.as_view(), 
        name='student_application_detail'),
    
    path('applications/<uuid:pk>/edit/', 
        views.StudentApplicationUpdateView.as_view(), 
        name='student_application_update'),
    
    path('applications/<uuid:pk>/submit/', 
        views.StudentApplicationSubmitView.as_view(), 
        name='student_application_submit'),
    
    path('applications/<uuid:pk>/withdraw/', 
        views.StudentApplicationWithdrawView.as_view(), 
        name='student_application_withdraw'),


    # =================================================================
    # 2. واجهات المراجعين (Reviewer System)
    # =================================================================
    path('reviewer/tasks/', 
        views.ReviewerTaskListView.as_view(), 
        name='reviewer_task_list'),
    
    path('reviewer/evaluate/<int:pk>/', 
        views.ApplicationScoringView.as_view(), 
        name='application_scoring'),
    
    path('reviewer/conflict/<int:pk>/', 
        views.ReviewConflictFlagView.as_view(), 
        name='review_conflict_flag'),


    # =================================================================
    # 3. واجهات اللجنة والإدارة (Committee & Admin)
    # =================================================================
    path('committee/dashboard/', 
        views.CommitteeHeadDashboardView.as_view(), 
        name='committee_dashboard'),
    
    path('committee/ranking/', 
        views.ApplicationRankListView.as_view(), 
        name='application_rank_list'),
    
    path('committee/decision/<uuid:pk>/', 
        views.FinalDecisionUpdateView.as_view(), 
        name='final_decision_update'),
    
    path('committee/distribute-auto/', 
        views.AutomatedDistributionView.as_view(), 
        name='automated_distribution'),
    
    path('committee/cycle/<int:pk>/transition/', 
        views.CycleStatusTransitionView.as_view(), 
        name='cycle_status_transition'),
    
]