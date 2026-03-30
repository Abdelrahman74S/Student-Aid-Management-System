from django.urls import path
from django.contrib.auth.views import PasswordResetDoneView, PasswordResetCompleteView, PasswordChangeDoneView
from .views import auth as views


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
    
    # Profile Management

]