import os
import time
from rest_framework import serializers

from video.models import Video, Parameters, VideoAsset


class ParametersSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parameters
        fields = ['data']  # 假设Parameters模型有data字段


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
    
    class Meta:
        model = Parameters
        fields = ['id', 'template_id', 'template_name', 'data', 'create_time', 'update_time', 'creator']
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

class VideoDetailSerializer(serializers.ModelSerializer):
    parameters = serializers.SerializerMethodField()
    
    class Meta:
        model = Video
        fields = ['id', 'title', 'creator', 'result', 'param_id', 'create_time', 'spec', 'parameters']
    
    def get_parameters(self, obj):
        if obj.param_id:
            try:
                param = Parameters.objects.get(id=obj.param_id)
                return ParametersSerializer(param).data
            except Parameters.DoesNotExist:
                return None
        return None

class VideoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Video
        fields = ['id', 'title', 'creator', 'result', 'process', 'param_id', 'create_time', 'spec']

class VideoAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoAsset
        fields = ['id', 'asset_name', 'origin', 'creator', 'duration', 'orientation', 'create_time', 'spec']
        read_only_fields = ['id', 'create_time']

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


class VideoAssetEditSerializer(serializers.Serializer):
    asset_id = serializers.CharField(max_length=100, help_text="视频素材ID")
    asset_name = serializers.CharField(max_length=255, help_text="视频素材名称")
    
    def validate_asset_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("素材名称不能为空")
        if len(value.strip()) > 255:
            raise serializers.ValidationError("素材名称长度不能超过255个字符")
        return value.strip()
