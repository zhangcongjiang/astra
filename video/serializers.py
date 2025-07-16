from rest_framework import serializers

from video.models import Video


class VideoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Video
        fields = ['id', 'title', 'creator', 'result', 'param_id', 'create_time', 'spec']
