from django.urls import path
from django.contrib.auth.views import PasswordResetDoneView, PasswordResetCompleteView, PasswordChangeDoneView
from .views import auth as views
from .views import profiles as view


app_name = 'accounts'

urlpatterns = [
    # Authentication
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.UserLoginView.as_view(), name='login'),
    path('logout/', views.UserLogoutView.as_view(), name='logout'),
    
    # Email Verification
    path('verify-email/<str:token>/', views.EmailVerificationView.as_view(), name='verify_email'),
    path('resend-verification/', views.ResendVerificationEmailView.as_view(), name='resend_verification'),
    
    # Password Reset
    path('password-reset/', views.CustomPasswordResetView.as_view(), name='password_reset'),
    
    path('password-reset/done/', PasswordResetDoneView.as_view(
        template_name='accounts/password_reset_done.html'
    ), name='password_reset_done'),
    
    path('password-reset/confirm/<uidb64>/<token>/', 
        views.CustomPasswordResetConfirmView.as_view(), 
        name='password_reset_confirm'),
    
    path('password-reset/complete/', PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset_complete.html'
    ), name='password_reset_complete'),
    
    # Password Change
    path('password/change/', views.ChangePasswordView.as_view(), name='change_password'),
    
    path('password/change/done/', PasswordChangeDoneView.as_view(
        template_name='accounts/password_change_done.html'
    ), name='password_change_done'),
    
    # -----------------------------------------------
    # Profile Management
    # -----------------------------------------------

    # Dashboard
    path('profile/', view.ProfileDashboardView.as_view(), name='profile_dashboard'),

    # Student Profile
    path('profile/student/', view.StudentProfileDetailView.as_view(), name='student_profile_detail'),
    path('profile/student/edit/', view.StudentProfileUpdateView.as_view(), name='student_profile_update'),

    # Reviewer Profile
    path('profile/reviewer/', view.ReviewerProfileDetailView.as_view(), name='reviewer_profile_detail'),
    path('profile/reviewer/edit/', view.ReviewerProfileUpdateView.as_view(), name='reviewer_profile_update'),

    # Committee Head Profile
    path('profile/committee-head/', view.CommitteeHeadProfileDetailView.as_view(), name='committee_head_profile_detail'),
    path('profile/committee-head/edit/', view.CommitteeHeadProfileUpdateView.as_view(), name='committee_head_profile_update'),

    # Auditor Profile
    path('profile/auditor/', view.AuditorProfileDetailView.as_view(), name='auditor_profile_detail'),
    path('profile/auditor/edit/', view.AuditorProfileUpdateView.as_view(), name='auditor_profile_update'),
    
]