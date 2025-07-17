from django.urls import path
from . import views

urlpatterns = [
    path('list/', views.TextListView.as_view(), name='text-list'),
    path('detail/<uuid:id>/', views.TextDetailView.as_view(), name='text-detail'),
    path('delete/', views.TextDeleteView.as_view(), name='text-delete'),
    path('download/<uuid:text_id>/', views.TextDownloadView.as_view(), name='text-download'),
    path('upload/', views.TextUploadView.as_view(), name='text-upload'),
]