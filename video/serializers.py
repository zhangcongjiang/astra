import os
import time

from django.contrib.auth.models import User
from rest_framework import serializers

from tag.models import Tag
from video.models import Video, Parameters, VideoAsset, VideoAssetTags


class ParametersSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()

    class Meta:
        model = Parameters
        fields = ['data', 'username']  # 假设Parameters模型有data字段

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username


class TemplateCache:
    """模板缓存类，用于缓存模板ID到名称的映射"""
    _cache = {}
    _cache_time = 0
    _cache_ttl = 300  # 缓存5分钟

    @classmethod
    def get_template_name_mapping(cls):
        """获取模板ID到名称的映射字典"""
        current_time = time.time()

        # 检查缓存是否过期
        if current_time - cls._cache_time > cls._cache_ttl or not cls._cache:
            cls._refresh_cache()
            cls._cache_time = current_time

        return cls._cache

    @classmethod
    def _refresh_cache(cls):
        """刷新缓存"""
        try:
            from video.templates.video_template import VideoTemplate
            template = VideoTemplate()
            templates = template.get_templates()

            # 构建ID到名称的映射字典
            cls._cache = {
                template_info.get('template_id'): template_info.get('name')
                for template_info in templates
                if template_info.get('template_id') and template_info.get('name')
            }
        except Exception:
            # 如果刷新失败，保持原有缓存
            pass

    @classmethod
    def clear_cache(cls):
        """清除缓存"""
        cls._cache = {}
        cls._cache_time = 0


class DraftSerializer(serializers.ModelSerializer):
    """草稿视频序列化器"""
    template_name = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Parameters
        fields = ['id', 'template_id', 'title', 'template_name', 'data', 'create_time', 'update_time', 'username']
        read_only_fields = ['id', 'create_time', 'update_time']

    def get_template_name(self, obj):
        """根据template_id获取模板名称 - 优化版本使用缓存"""
        if not obj.template_id:
            return None

        try:
            # 使用缓存获取模板名称映射
            template_mapping = TemplateCache.get_template_name_mapping()
            return template_mapping.get(str(obj.template_id))
        except Exception:
            return None

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username


class VideoDetailSerializer(serializers.ModelSerializer):
    parameters = serializers.SerializerMethodField()

    class Meta:
        model = Video
        fields = ['id', 'title', 'creator', 'video_type', 'content', 'cover', 'vertical_cover', 'cost', 'size', 'result', 'param_id', 'create_time',
                  'spec',
                  'parameters']

    def get_parameters(self, obj):
        if obj.param_id:
            try:
                param = Parameters.objects.get(id=obj.param_id)
                return ParametersSerializer(param).data
            except Parameters.DoesNotExist:
                return None
        return None


class VideoSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()

    class Meta:
        model = Video
        fields = ['id', 'title', 'username', 'video_path', 'content', 'cover', 'vertical_cover', 'cost', 'size', 'video_type', 'result', 'process',
                  'param_id',
                  'create_time', 'spec']

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username


class VideoAssetSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()

    class Meta:
        model = VideoAsset
        fields = ['id', 'asset_name', 'tags', 'origin', 'username', 'duration', 'orientation', 'create_time', 'spec']
        read_only_fields = ['id', 'create_time']

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username

    def get_tags(self, obj):
        # 手动查询 SoundTags 表
        video_asset_tags = VideoAssetTags.objects.filter(asset_id=obj.id)
        tags = []
        for video_asset_tag in video_asset_tags:
            try:
                tag = Tag.objects.get(id=video_asset_tag.tag_id)
                tags.append({
                    'id': tag.id,
                    'tag_name': tag.tag_name,
                    'parent': tag.parent,
                    'category': tag.category
                })
            except Tag.DoesNotExist:
                continue
        return tags


class VideoAssetUploadSerializer(serializers.ModelSerializer):
    video_file = serializers.FileField(write_only=True)

    class Meta:
        model = VideoAsset
        fields = ['video_file', 'creator', 'spec']

    def validate_video_file(self, value):
        # 验证文件类型
        allowed_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm']
        file_extension = os.path.splitext(value.name)[1].lower()
        if file_extension not in allowed_extensions:
            raise serializers.ValidationError("只支持视频文件格式: mp4, avi, mov, mkv, wmv, flv, webm")

        # 验证文件大小 (例如限制为500MB)
        max_size = 500 * 1024 * 1024  # 500MB
        if value.size > max_size:
            raise serializers.ValidationError("视频文件大小不能超过500MB")

        return value


class VideoUploadSerializer(serializers.Serializer):
    video_id = serializers.CharField(write_only=True)
    video_file = serializers.FileField(write_only=True)

    def validate_video_file(self, value):
        # 验证文件类型
        allowed_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm']
        file_extension = os.path.splitext(value.name)[1].lower()
        if file_extension not in allowed_extensions:
            raise serializers.ValidationError("只支持视频文件格式: mp4, avi, mov, mkv, wmv, flv, webm")

        # 验证文件大小 (例如限制为500MB)
        max_size = 500 * 1024 * 1024  # 500MB
        if value.size > max_size:
            raise serializers.ValidationError("视频文件大小不能超过500MB")

        return value


class VideoCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=30)
    content = serializers.CharField(required=False, allow_blank=True)
    video_file = serializers.FileField(required=False, write_only=True)
    cover = serializers.FileField(required=False, write_only=True)
    vertical_cover = serializers.FileField(required=False, write_only=True)

    def validate_video_file(self, value):
        # 验证文件类型
        allowed_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm']
        file_extension = os.path.splitext(value.name)[1].lower()
        if file_extension not in allowed_extensions:
            raise serializers.ValidationError("只支持视频文件格式: mp4, avi, mov, mkv, wmv, flv, webm")

        # 验证文件大小 (限制为500MB)
        max_size = 500 * 1024 * 1024  # 500MB
        if value.size > max_size:
            raise serializers.ValidationError("视频文件大小不能超过500MB")

        return value

    def validate_cover(self, value):
        # 验证封面文件类型
        allowed_types = ['image/jpeg', 'image/jpg', 'image/png']
        content_type = getattr(value, 'content_type', None)
        if content_type not in allowed_types:
            raise serializers.ValidationError("不支持的文件类型，请上传 JPG、PNG格式的图片")

        # 验证封面文件大小 (5MB)
        max_size = 5 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError("封面文件大小不能超过5MB")

        return value
