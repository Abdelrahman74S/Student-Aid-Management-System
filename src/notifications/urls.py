from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    # الإشعارات
    path('', views.NotificationListView.as_view(), name='list'),
    path('<uuid:pk>/read/', views.NotificationMarkReadView.as_view(), name='mark_read'),
    path('mark-all-read/', views.NotificationMarkAllReadView.as_view(), name='mark_all_read'),
    path('api/unread-count/', views.UnreadCountAPIView.as_view(), name='unread_count_api'),

    # تظلمات الطالب
    path('appeals/', views.AppealListView.as_view(), name='appeal_list'),
    path('appeals/new/<uuid:app_id>/', views.AppealCreateView.as_view(), name='appeal_create'),

    # مراجعة التظلمات (اللجنة)
    path('appeals/review/', views.AppealReviewListView.as_view(), name='appeal_review_list'),
    path('appeals/review/<uuid:pk>/', views.AppealReviewUpdateView.as_view(), name='appeal_review'),
]
