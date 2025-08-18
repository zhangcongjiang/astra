from django.urls import path

from .views import NewsListView, NewsTrendView, NewsDetailView, AddNewsToAssetView

urlpatterns = [
    path('', NewsListView.as_view(), name='news-list'),
    path('detail/', NewsDetailView.as_view(), name='news-detail'),
    path('trend/', NewsTrendView.as_view(), name='news-trend'),
    path('add-to-asset/', AddNewsToAssetView.as_view(), name='add-news-to-asset'),
]
