from django.urls import path
# استيراد ملفات الـ Views بشكل صريح
from .views import auth_views, student_views, reviewer_views, committee_views, admin_views

app_name = 'accounts'

urlpatterns = [
    # --- 1. Auth URLs (auth_views.py) ---
    path('register/', auth_views.StudentRegistrationView.as_view(), name='register'),
    path('login/', auth_views.CustomLoginView.as_view(), name='login'),
    path('logout/', auth_views.CustomLogoutView.as_view(), name='logout'),
    path('profile/edit/', auth_views.ProfileUpdateView.as_view(), name='profile_edit'),
    path('dashboard/', auth_views.DashboardRedirectView.as_view(), name='dashboard_redirect'),
    
    # --- 2. Student URLs (student_views.py) ---
    path('student/dashboard/', student_views.StudentDashboardView.as_view(), name='student_dashboard'),
    path('student/profile/edit/', student_views.StudentProfileUpdateView.as_view(), name='student_profile_edit'),
    path('programs/', student_views.ProgramListView.as_view(), name='program_list'),
    
    # --- 3. Reviewer URLs (reviewer_views.py) ---
    path('reviewer/dashboard/', reviewer_views.ReviewerDashboardView.as_view(), name='reviewer_dashboard'),
    path('reviewer/profile/edit/', reviewer_views.ReviewerProfileUpdateView.as_view(), name='reviewer_profile_edit'),
    path('reviewer/students/', reviewer_views.AssignedStudentsView.as_view(), name='assigned_students'),
    path('reviewer/student/<uuid:pk>/approve/', reviewer_views.QuickStudentApproveView.as_view(), name='quick_approve'),
    
    # --- 4. Committee Head URLs (committee_views.py) ---
    path('committee/dashboard/', committee_views.CommitteeDashboardView.as_view(), name='committee_dashboard'),
    path('committee/profile/edit/', committee_views.CommitteeProfileUpdateView.as_view(), name='committee_profile_edit'),
    path('committee/document/<int:document_id>/sign/', committee_views.DocumentSignView.as_view(), name='document_sign'),
    path('committee/members/', committee_views.CommitteeMembersView.as_view(), name='committee_members'),
    
    # --- 5. Admin URLs (admin_views.py) ---
    path('admin/dashboard/', admin_views.AdminDashboardView.as_view(), name='admin_dashboard'),
    path('admin/users/', admin_views.UserManagementView.as_view(), name='user_management'),
    path('admin/user/<uuid:pk>/role/', admin_views.UserRoleUpdateView.as_view(), name='user_role_update'),
    path('admin/user/<uuid:pk>/verify/', admin_views.UserVerifyView.as_view(), name='user_verify'),
    path('admin/programs/', admin_views.ProgramCRUDView.as_view(), name='program_management'),
]