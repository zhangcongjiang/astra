from django.urls import path
from . import views

urlpatterns = [
    path('list/', views.TextListView.as_view(), name='text-list'),
    path('detail/<uuid:id>/', views.TextDetailView.as_view(), name='text-detail'),
    path('delete/', views.TextDeleteView.as_view(), name='text-delete'),
    path('download/<uuid:text_id>/', views.TextDownloadView.as_view(), name='text-download'),
    path('upload/', views.TextUploadView.as_view(), name='text-upload'),
    path('save/', views.TextSaveView.as_view(), name='text-save'),
    # 在现有的urlpatterns中添加
    path('import-url/', views.TextUrlImportView.as_view(), name='text-url-import'),
    path('cover/replace/', views.TextCoverReplaceView.as_view(), name='text-cover-replace'),
]