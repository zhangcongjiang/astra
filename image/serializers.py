from rest_framework import serializers

from image.models import Image, ImageTags


class ImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Image
        fields = '__all__'


class ImageTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImageTags
        fields = ['image_id', 'tag_id']


class BindTagsSerializer(serializers.Serializer):
    image_id = serializers.UUIDField()
    tag_ids = serializers.ListField(child=serializers.UUIDField())
