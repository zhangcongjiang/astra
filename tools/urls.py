from django.urls import path

from tools.views import ToolUploadView, ToolCategoryView
from tools.image_search_views import ImageSearchView, SaveImageView, AddToAssetView, ImageAddressView

urlpatterns = [
    path('upload/', ToolUploadView.as_view(), name='upload_tool'),
    path('category/', ToolCategoryView.as_view(), name='category_tool'),

    # 图片搜索相关接口
    path('image/search/', ImageSearchView.as_view(), name='image_search'),
    path('image/address/', ImageAddressView.as_view(), name='image_address'),
    path('image/save/', SaveImageView.as_view(), name='save_image'),
    path('image/add-to-asset/', AddToAssetView.as_view(), name='add_to_asset'),
]
