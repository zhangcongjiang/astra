from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from common.response import error_response, ok_response
from tag.models import Tag
from tag.serializers import TagSerializer


# Create your views here.
class TagViewSet(viewsets.ModelViewSet):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    http_method_names = ['get', 'post']

    @swagger_auto_schema(
        operation_description="根据类型查询标签",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['name', 'parent', 'category'],
            properties={
                'tag_name': openapi.Schema(type=openapi.TYPE_STRING, description='标签名称'),
                'parent': openapi.Schema(type=openapi.TYPE_STRING, description='父标签'),
                'category': openapi.Schema(type=openapi.TYPE_STRING, description='标签类别')
            }
        ),
        responses={
            200: openapi.Response(
                description="Tag add successfully",
                examples={
                    "application/json": {
                        'code': 0,
                        "message": "Tag add successfully",
                        "data": ""
                    }
                }
            ),
            500: openapi.Response(
                description="Internal Server Error",
                examples={
                    "application/json": {
                        'code': 1,
                        "message": "fail",
                        "data": ""
                    }
                }
            ),
        }
    )
    @action(detail=False, methods=['post'], url_path='add')
    def create_tag(self, request, *args, **kwargs):
        try:
            serializer = self.serializer_class(data=request.data)
            if not serializer.is_valid():
                return error_response(serializer.errors)

            tag_name = serializer.validated_data['tag_name']
            parent = serializer.validated_data['parent']
            category = serializer.validated_data['category']

            new_tag = Tag(tag_name=tag_name, parent=parent, category=category)
            new_tag.save()

            return ok_response(self.serializer_class(new_tag).data)
        except Exception as e:
            return error_response(str(e))

    @swagger_auto_schema(
        operation_description="根据类型查询所有标签",
        responses={200: openapi.Response(
                description="Tag list successfully",
                examples={
                    "application/json": {
                        'code': 0,
                        "message": "Tag add successfully",
                        "data": ""
                    }
                }
            )},
        manual_parameters=[
            openapi.Parameter('category', openapi.IN_QUERY, description="type of tag", type=openapi.TYPE_STRING, enum=['IMAGE', 'VIDEO', 'SOUND'],
                              default='IMAGE'),
        ]
    )
    @action(detail=False, methods=['get'], url_path='category')
    def get(self, request, *args, **kwargs):
        category = self.request.query_params.get('category')
        try:
            parent_tags = self.queryset.filter(category=category, parent='')
            parent_tags = self.serializer_class(parent_tags, many=True).data
            for item in parent_tags:
                tags = self.queryset.filter(category=category, parent=item.get('id'))
                item['children'] = self.serializer_class(tags, many=True).data

            return ok_response(parent_tags)
        except Exception as e:
            return error_response(str(e))
