from rest_framework import serializers
from .models import News, NewsDetails, NewsMedia


class NewsDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsDetails
        fields = '__all__'


class NewsMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsMedia
        fields = '__all__'


class NewsSerializer(serializers.ModelSerializer):
    class Meta:
        model = News
        fields = '__all__'
