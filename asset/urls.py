from django.urls import path
from . import views
from .views import TextAssetCreateView, TextAssetUpdateView, ResourceDetailView

urlpatterns = [
    # 素材集管理
    path('list/', views.AssetListView.as_view(), name='asset-list'),
    path('detail/<uuid:asset_id>/', views.AssetDetailView.as_view(), name='asset-detail'),
    path('create/', views.AssetCreateView.as_view(), name='asset-create'),
    path('update/', views.AssetUpdateView.as_view(), name='asset-update'),
    path('delete/', views.AssetDeleteView.as_view(), name='asset-delete'),

    # 素材管理
    path('asset-info/create/', views.AssetInfoCreateView.as_view(), name='asset-info-create'),
    path('asset-info/delete/', views.AssetInfoDeleteView.as_view(), name='asset-info-delete'),
    path('asset-info/reorder/', views.AssetInfoReorderView.as_view(), name='asset-info-reorder'),
    
    # 文本素材管理
    path('text/create/', TextAssetCreateView.as_view(), name='text-asset-create'),
    path('text/update/', TextAssetUpdateView.as_view(), name='text-asset-update'),
    
    # 资源详情查询
    path('resource/detail/', ResourceDetailView.as_view(), name='resource-detail'),
]
