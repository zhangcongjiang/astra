import os
from datetime import timedelta

import requests
from PIL import Image as PILImage
from django.db import connection
from django.db.models import Q
from django.utils import timezone
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from astra.settings import IMG_PATH
from common.response import ok_response, error_response
from image.models import Image
from news.collector.baidu_collector import BaiduCollector
from news.collector.remote_img_downloader import download
from news.collector.toutiao_collector import ToutiaoCollector
from news.collector.weibo_collector import WeiboCollector
from news.models import News, NewsDetails, NewsMedia, NewsTrend
from news.serializers import NewsSerializer, NewsDetailsSerializer, NewsMediaSerializer


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'pageSize'
    max_page_size = 1000

    def get_paginated_response(self, data):
        return ok_response(data={
            'results': data,
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'page_size': self.page_size,
            'current_page': self.page.number,
            'total_pages': self.page.paginator.num_pages,
        })


class NewsListView(generics.ListAPIView):
    serializer_class = NewsSerializer
    pagination_class = StandardResultsSetPagination
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="获取新闻列表",
        operation_description="获取新闻列表，支持按平台、时间范围、标题、分类筛选和排序",
        manual_parameters=[
            openapi.Parameter('platform', openapi.IN_QUERY, description="平台筛选", type=openapi.TYPE_STRING),
            openapi.Parameter('time_range', openapi.IN_QUERY, description="时间范围 (1d/3d/1w/1m/1y/3y)", type=openapi.TYPE_STRING, default='1d'),
            openapi.Parameter('title', openapi.IN_QUERY, description="标题关键词搜索", type=openapi.TYPE_STRING),
            openapi.Parameter('category', openapi.IN_QUERY, description="分类筛选", type=openapi.TYPE_STRING),
            openapi.Parameter('sort_by', openapi.IN_QUERY, description="排序方式 (hot/time)", type=openapi.TYPE_STRING, default='hot'),
        ]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        platform = self.request.query_params.get('platform')
        time_range = self.request.query_params.get('time_range', '1d')
        title = self.request.query_params.get('title', '')
        category = self.request.query_params.get('category', '')
        sort_by = self.request.query_params.get('sort_by', 'hot')

        query = Q()

        if platform:
            query &= Q(platform=platform)
        if category and category != '其他':
            query &= Q(category=category)
        if title:
            query &= (Q(title__icontains=title) | Q(tag__icontains=title))

        # 时间过滤逻辑
        now = timezone.now()
        if time_range == '1d':
            # 1天内
            start_time = now - timedelta(days=1)
            query &= Q(date__gte=start_time)
        elif time_range == '3d':
            # 3天内
            start_time = now - timedelta(days=3)
            query &= Q(date__gte=start_time)
        elif time_range == '1w':
            # 1周内
            start_time = now - timedelta(weeks=1)
            query &= Q(date__gte=start_time)
        elif time_range == '1m':
            # 1个月内
            start_time = now - timedelta(days=30)
            query &= Q(date__gte=start_time)
        elif time_range == '1y':
            # 1年内
            start_time = now - timedelta(days=365)
            query &= Q(date__gte=start_time)
        elif time_range == '3y':
            # 3年内
            start_time = now - timedelta(days=365 * 3)
            query &= Q(date__gte=start_time)
        # 如果time_range不在支持的范围内，则不添加时间过滤条件，返回所有数据

        # 排序逻辑
        if sort_by == 'time':
            queryset = News.objects.filter(query).order_by('-date', 'rank')
        elif sort_by == 'rank':  # 默认按热度排序
            queryset = News.objects.filter(query).order_by('rank', '-date')
        else:
            queryset = News.objects.filter(query).order_by('-hots', '-date')

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return ok_response(serializer.data)


class NewsDetailView(generics.RetrieveAPIView):
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = NewsDetailsSerializer  # 创建一个新的serializer用于包含news详情和media

    @swagger_auto_schema(
        operation_description="Retrieve details of a news item including its media",
        responses={200: NewsDetailsSerializer()},
        manual_parameters=[
            openapi.Parameter('news_id', openapi.IN_QUERY, description="ID of the news item", type=openapi.TYPE_STRING),
        ]
    )
    def get(self, request, *args, **kwargs):
        news_id = self.request.query_params.get('news_id')

        try:
            news = News.objects.get(news_id=news_id)
        except News.DoesNotExist:
            return error_response("未找到该新闻")
        user = request.user.id
        # 获取NewsDetails
        try:
            news_details = NewsDetails.objects.get(news_id=news_id)
            news_details_serializer = NewsDetailsSerializer(news_details)
        except NewsDetails.DoesNotExist:
            if news.platform == '微博':
                WeiboCollector().collect(
                    url=f"https://m.weibo.cn/api/container/getIndex?containerid=100103type%3D1%26q%3D%23{news.title}%23&page_type=searchall",
                    news_id=news_id, user=user)
                news_details = NewsDetails.objects.get(news_id=news_id)
                news_details_serializer = NewsDetailsSerializer(news_details)
            elif news.platform == '百度':
                href = news.href
                BaiduCollector().collect(href, news_id=news_id, user=user)
                news_details = NewsDetails.objects.get(news_id=news_id)
                news_details_serializer = NewsDetailsSerializer(news_details)
            elif news.platform == '今日头条':
                href = news.href
                ToutiaoCollector().collect(href, news_id=news_id, user=user)
                news_details = NewsDetails.objects.get(news_id=news_id)
                news_details_serializer = NewsDetailsSerializer(news_details)
        except Exception:
            news_details = NewsDetails(news_id=news_id, msg='详细信息获取中')
            news_details_serializer = NewsDetailsSerializer(news_details)

        # 获取NewsMedia
        news_media = NewsMedia.objects.filter(news_id=news_id, media_type='IMG')
        for item in news_media:
            img_name = item.media
            file_path = os.path.join(IMG_PATH, img_name)
            if not os.path.exists(file_path):
                # NBA官网的照片有访问时限，因此必现爬取的时候就进行下载
                if news.platform == 'NBA官网':
                    download(item.media)
                    img_name = item.media.split('/')[-1]
                else:
                    response = requests.get(item.href)
                    with open(file_path, 'wb') as f:
                        f.write(response.content)
                pil_image = PILImage.open(file_path)
                width, height = pil_image.size
                image_format = pil_image.format
                image_mode = pil_image.mode

                spec = {
                    'format': image_format,
                    'mode': image_mode
                }

                Image(
                    img_name=img_name,
                    category='normal',
                    img_path=IMG_PATH,
                    width=int(width),
                    height=int(height),
                    origin='热点新闻',
                    creator=request.user.id,
                    spec=spec
                ).save()

        news_media_serializer = NewsMediaSerializer(news_media, many=True)

        response_data = {
            'news': NewsSerializer(news).data,
            'details': news_details_serializer.data if news_details_serializer else None,
            'media': news_media_serializer.data,
        }

        return ok_response(response_data)


class NewsTrendView(APIView):
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Retrieve the trend of rank and hots over time for a specific news title",
        responses={200: 'Trend data retrieved successfully'},
        manual_parameters=[
            openapi.Parameter('news_id', openapi.IN_QUERY, description="News id", type=openapi.TYPE_STRING, required=True)

        ]
    )
    def get(self, request, *args, **kwargs):
        news_id = request.query_params.get('news_id')
        trend_data = []

        with connection.cursor() as cursor:
            cursor.execute("""
                    SELECT date, rank, hots 
                    FROM public.news_newstrend 
                    WHERE news_id = %s 
                    ORDER BY date
                """, [news_id])

            for row in cursor:
                trend_data.append({
                    'date': row[0].strftime('%Y-%m-%dT%H:%M:%S'),
                    'rank': row[1],
                    'hots': row[2]
                })

        return ok_response(trend_data)
