from django.urls import path
from . import views

urlpatterns = [
    path('settings/update/', views.SystemSettingsAPIView.as_view(), name='system_settings_update'),
    path('settings/', views.SystemSettingsQueryView.as_view(), name='system_settings_query'),
    path('users/', views.UserListView.as_view(), name='user_list'),
]