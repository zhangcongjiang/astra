from django.urls import path
from . import views

urlpatterns = [
    # 认证相关
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('user-info/', views.UserInfoView.as_view(), name='user_info'),
    
    # 系统设置相关
    path('settings/update/', views.SystemSettingsAPIView.as_view(), name='system_settings_update'),
    path('settings/', views.SystemSettingsQueryView.as_view(), name='system_settings_query'),
    path('users/', views.UserListView.as_view(), name='user_list'),
    path('users/current/', views.CurrentUserView.as_view(), name='current_user'),

    # 自媒体账号相关
    path('media-accounts/', views.MediaAccountListCreateView.as_view(), name='media_account_list_create'),
    path('media-accounts/<pk>/', views.MediaAccountUpdateView.as_view(), name='media_account_update'),
]
