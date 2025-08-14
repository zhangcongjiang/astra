from django.db import models


class News(models.Model):
    news_id = models.CharField(max_length=36)
    title = models.TextField()  # 标题
    rank = models.IntegerField()  # 热搜排行
    hots = models.IntegerField(default=0)  # 热度
    category = models.CharField(max_length=16)  # 类别
    href = models.TextField(blank=True)  # 链接
    platform = models.CharField(max_length=16)  # 平台
    date = models.DateTimeField('news happened')  # 时间
    tag = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"title:{self.title}, platform:{self.platform}"


# 新闻热度和排名变化趋势
class NewsTrend(models.Model):
    news_id = models.CharField(max_length=36)
    rank = models.IntegerField()  # 热搜排行
    category = models.CharField(max_length=16, blank=True, null=True)  # 类别
    hots = models.IntegerField(default=0)  # 热度
    date = models.DateTimeField(auto_now_add=True)  # 时间
    spec = models.JSONField(default=dict, null=True)


# 消息详情，爬取后进行存储，避免重复爬
class NewsDetails(models.Model):
    news_id = models.CharField(max_length=36)
    msg = models.TextField(blank=True, null=True)  # 新闻内容


# 新闻关联的媒体信息
class NewsMedia(models.Model):
    news_id = models.CharField(max_length=36)
    media_type = models.CharField(max_length=16)  # 视频、音频、图片
    media = models.TextField()
    href = models.TextField()
