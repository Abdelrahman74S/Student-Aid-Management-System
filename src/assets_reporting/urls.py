from django.urls import path
from . import views

app_name = 'assets_reporting'

urlpatterns = [
    # --- 1. روابط الطالب (المستندات وقسائم الصرف) ---
    path('my-documents/', views.StudentDocumentListView.as_view(), name='document_list'),
    path('documents/upload/', views.DocumentUploadView.as_view(), name='document_upload'),
    path('documents/<uuid:pk>/delete/', views.DocumentDeleteView.as_view(), name='document_delete'),
    path('my-voucher/<uuid:app_id>/', views.DisbursementVoucherDetailView.as_view(), name='voucher_detail'),

    # --- 2. روابط الباحث الاجتماعي (البحث الميداني) ---
    path('research/create/<uuid:app_id>/', views.SocialResearchCreateView.as_view(), name='social_research_create'),
    path('research/edit/<int:pk>/', views.SocialResearchUpdateView.as_view(), name='social_research_update'),

    # --- 3. روابط رئيس اللجنة (المحاضر والتقارير الرسمية) ---
    path('meetings/', views.CommitteeMeetingListView.as_view(), name='meeting_list'),
    path('meetings/create/', views.CommitteeMeetingCreateView.as_view(), name='meeting_create'),
    path('meetings/<int:pk>/', views.CommitteeMeetingDetailView.as_view(), name='meeting_detail'),
    path('reports/', views.OfficialReportListView.as_view(), name='report_list'),
    path('reports/<uuid:pk>/', views.OfficialReportDetailView.as_view(), name='report_detail'),

    # --- 4. روابط الإدارة والخزينة (التحقق من الصرف) ---
    path('vouchers/verify/', views.VoucherVerifyView.as_view(), name='voucher_verify'),
]