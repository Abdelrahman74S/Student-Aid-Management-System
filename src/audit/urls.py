from django.urls import path
from . import views

app_name = 'audit'

urlpatterns = [
    # لوحة التحكم الرئيسية للمراقب
    path('dashboard/', views.AuditDashboardView.as_view(), name='dashboard'),

    # سجلات تعديل البيانات (إضافة، تعديل، حذف)
    path('logs/data/', views.DataAuditListView.as_view(), name='data_audit_list'),

    # سجلات الوصول (الدخول، الخروج، وفشل الدخول)
    path('logs/access/', views.AccessLogListView.as_view(), name='access_log_list'),

    # السجل الزمني لتغيير حالات الطلبات
    path('logs/timeline/', views.AuditTimelineView.as_view(), name='timeline'),

    # سجل التجاوزات الإدارية الاستثنائية
    path('logs/overrides/', views.OverrideLogListView.as_view(), name='override_log_list'),

    # سجل تدقيق الميزانية وتغيير المبالغ
    path('logs/budget/', views.BudgetAuditListView.as_view(), name='budget_audit_list'),

    # سجل القرارات الإدارية الكبرى
    path('logs/actions/', views.ProcessActionListView.as_view(), name='process_action_list'),
]