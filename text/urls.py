from django.urls import path
from . import views

urlpatterns = [
    path('list/', views.TextListView.as_view(), name='text-list'),
    path('detail/<uuid:id>/', views.TextDetailView.as_view(), name='text-detail'),
    path('delete/', views.TextDeleteView.as_view(), name='text-delete'),
    path('batch-delete/', views.TextBatchDeleteView.as_view(), name='text-batch-delete'),
    path('download/<uuid:text_id>/', views.TextDownloadView.as_view(), name='text-download'),
    path('upload/', views.TextUploadView.as_view(), name='text-upload'),
    path('save/', views.TextSaveView.as_view(), name='text-save'),
    # 在现有的urlpatterns中添加
    path('import-url/', views.TextUrlImportView.as_view(), name='text-url-import'),
    path('cover/replace/', views.TextCoverReplaceView.as_view(), name='text-cover-replace'),

    # Dynamic APIs
    path('dynamic/list/', views.DynamicListView.as_view(), name='dynamic-list'),
    path('dynamic/detail/<uuid:id>/', views.DynamicDetailView.as_view(), name='dynamic-detail'),
    path('dynamic/create/', views.DynamicCreateView.as_view(), name='dynamic-create'),
    path('dynamic/delete/', views.DynamicDeleteView.as_view(), name='dynamic-delete'),
    path('dynamic/batch-delete/', views.DynamicBatchDeleteView.as_view(), name='dynamic-batch-delete'),
]