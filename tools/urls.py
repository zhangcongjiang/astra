from django.urls import path

from tools.views import ToolUploadView, ToolCategoryView

urlpatterns = [
    path('upload/', ToolUploadView.as_view(), name='upload_tool'),
    path('category/', ToolCategoryView.as_view(), name='category_tool'),

]
