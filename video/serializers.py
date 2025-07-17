from rest_framework import serializers

from video.models import Video, Parameters


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
