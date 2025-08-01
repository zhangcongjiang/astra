from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.contrib.auth.models import User

from account.models import SystemSettings
from account.serializers import SystemSettingsSerializer, SystemSettingsQuerySerializer, UserListSerializer
from common.response import error_response, ok_response


# Create your views here.
class SystemSettingsAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="系统设置内容更新",
        request_body=SystemSettingsSerializer,
        responses={
            0: "更新成功",
            1: "更新失败",
        },
    )
    def post(self, request):
        # 验证输入数据
        serializer = SystemSettingsSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("无效的输入")
        user_id = request.user.id
        key = serializer.validated_data['key']
        value = serializer.validated_data['value']
        try:
            settings = SystemSettings.objects.filter(user=user_id, key=key)
            if len(settings) != 1:
                return error_response("系统错误，请联系管理员")
            else:
                setting = settings[0]
                exist_values = setting.value
                for k, v in value:
                    exist_values[k] = v
                setting.value = exist_values
                setting.save()
            return ok_response("更新成功")
        except Exception:
            return error_response("系统错误，请联系管理员")


class SystemSettingsQueryView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="根据key查询系统设置",
        query_serializer=SystemSettingsQuerySerializer,
        responses={
            0: "查询成功",
            1: "查询失败",
        },
    )
    def get(self, request):
        # 验证输入参数
        serializer = SystemSettingsQuerySerializer(data=request.query_params)
        if not serializer.is_valid():
            return error_response("无效的输入参数")

        user_id = request.user.id
        key = serializer.validated_data['key']

        try:
            # 查询用户的特定配置
            setting = SystemSettings.objects.filter(user=user_id, key=key).first()
            if setting:
                data = {
                    'key': setting.key,
                    'value': setting.value
                }
                return ok_response(data=data, message="查询成功")
            else:
                return error_response("未找到对应的配置项")
        except Exception as e:
            return error_response("系统错误，请联系管理员")


class UserListView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="查询所有用户名",
        responses={
            200: UserListSerializer(many=True),
        },
    )
    def get(self, request):
        """获取所有用户的ID和用户名"""
        try:
            # 查询所有用户，只获取id和username字段
            users = User.objects.all().values('id', 'username', 'is_superuser')

            # 转换为列表格式
            user_list = list(users)

            return ok_response(data=user_list, message="查询成功")
        except Exception as e:
            return error_response("系统错误，请联系管理员")
