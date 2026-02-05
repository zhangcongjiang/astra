import uuid

from django.db import models


class SystemSettings(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.CharField(max_length=36, blank=True)
    key = models.CharField(max_length=36, blank=False)
    value = models.JSONField(default=dict, null=True, blank=True)


class MediaAccount(models.Model):
    PLATFORM_CHOICES = [
        ('TOUTIAO', '今日头条'),
        ('BAIDU', '百度'),
        ('DOUYIN', '抖音'),
        ('WEIXIN_CHANNEL', '视频号'),
        ('WEIXIN', '公众号'),
        ('REDNOTE', '小红书'),
        ('BILIBILI', 'B站'),
        ('WEIBO', '微博'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.CharField(max_length=36, blank=True)
    name = models.CharField(max_length=36, blank=False)
    platform = models.CharField(max_length=16, blank=True, choices=PLATFORM_CHOICES)
    main_page = models.TextField(blank=True)
