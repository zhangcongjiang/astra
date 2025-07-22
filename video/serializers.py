import os
from rest_framework import serializers

from video.models import Video, Parameters, VideoAsset


class ParametersSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parameters
        fields = ['data']  # 假设Parameters模型有data字段

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
