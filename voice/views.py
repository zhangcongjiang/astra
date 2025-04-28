import configparser
import logging
import os
import uuid
from datetime import datetime
from io import BytesIO

from django.db.models import Q
from django.utils import timezone
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from pydub import AudioSegment
from rest_framework import generics
from rest_framework.authentication import TokenAuthentication
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from astra.settings import EFFECT_PATH, SOUND_PATH, BGM_PATH, SEED_PATH
from common.response import error_response, ok_response
from tag.models import Tag
from voice.models import Sound, SoundTags, Speaker, SpeakerTags
from voice.serializers import SoundSerializer, SoundBindTagsSerializer, SpeakerSerializer
from voice.text_to_speech import Speech

TIME_FORMAT = '%Y-%m-%dT%H:%M:%S'

SOUND_DIR = {
    'SOUND': SOUND_PATH,
    'BGM': BGM_PATH,
    'EFFECT': EFFECT_PATH
}
logger = logging.getLogger("voice")

conf_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sound.ini")
cf = configparser.ConfigParser()
cf.read(conf_path, encoding='utf-8')
DEFAULT_SAMPLE_TEXT = cf.get('default', 'Audio_Sample_Text')


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        return ok_response(data={
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })


class SoundUploadView(generics.CreateAPIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_serializer_class(self):
        return None

    @swagger_auto_schema(
        operation_description="上传音频特效",
        manual_parameters=[
            openapi.Parameter(
                'file', openapi.IN_FORM, description="音频文件", type=openapi.TYPE_FILE, required=True
            ),
            openapi.Parameter(
                'name', openapi.IN_FORM, description="音频名称", type=openapi.TYPE_STRING, required=True
            ),
            openapi.Parameter(
                'desc', openapi.IN_FORM, description="描述信息", type=openapi.TYPE_STRING,
            ),
            openapi.Parameter(
                'category', openapi.IN_FORM, description="音频分类 (SOUND: 普通音频, BGM: 背景音乐, EFFECT: 特效音)", enum=['SOUND', 'BGM', 'EFFECT'],
                type=openapi.TYPE_STRING, default='SOUND', required=True
            ),
        ],
        responses={
            200: openapi.Response(
                description="音频特效上传成功",
                examples={
                    "application/json": {
                        "code": 0,
                        "data": "sound_path",
                        "msg": "success"
                    }
                }
            )
        }
    )
    def post(self, request, *args, **kwargs):
        file = request.FILES.get('file')
        name = request.data.get('name')
        desc = request.data.get('desc', '')
        category = request.data.get('category')
        if not file:
            return error_response("未提供音频特效")
        sound_format = file.name.split('.')[-1]
        if sound_format not in ['mp3', 'wav']:
            return error_response("只支持wav、mp3格式音频特效")
        if category not in ['BGM', 'EFFECT', 'SOUND']:
            return error_response("分类必须是 BGM EFFECT或 SOUND")

        filename = f"{str(uuid.uuid4())}.{file.name.split('.')[-1]}"
        file_path = os.path.join(SOUND_DIR.get(category), filename)

        with open(file_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)
            # 获取音频时长
        try:
            # 将文件对象转换为 BytesIO
            file.seek(0)  # 确保文件指针在开头
            audio_data = BytesIO(file.read())
            audio = AudioSegment.from_file(audio_data, format=sound_format)
            duration = len(audio) / 1000.0  # 将毫秒转换为秒
        except Exception as e:
            return error_response(f"无法解析音频文件: {str(e)}")
        spec = {
            'duration': round(duration, 2),
            'format': sound_format
        }
        Sound(name=name, sound_path=filename, desc=desc, spec=spec, category=category).save()

        return ok_response("ok")


class SoundListView(generics.ListAPIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = SoundSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        start_datetime_str = self.request.query_params.get('start_datetime', '1970-01-01T00:00:00')
        end_datetime_str = self.request.query_params.get('end_datetime', datetime.now().strftime(TIME_FORMAT))
        tag_id = self.request.query_params.get('tag_id', '')
        sort_by = self.request.query_params.get('sort_by', 'create_time')
        order = self.request.query_params.get('order', 'asc')
        category = self.request.query_params.get('category', 'SOUND')
        try:
            start_datetime = timezone.make_aware(datetime.strptime(start_datetime_str, TIME_FORMAT))
            end_datetime = timezone.make_aware(datetime.strptime(end_datetime_str, TIME_FORMAT))
        except ValueError:
            return Sound.objects.none()

        if end_datetime <= start_datetime:
            return Sound.objects.none()

        query = Q()

        if tag_id:
            try:
                tag = Tag.objects.get(id=tag_id)
                if tag.parent == '':
                    child_tags = Tag.objects.filter(parent=tag).values_list('id', flat=True)
                    sound_ids = SoundTags.objects.filter(tag_id__in=child_tags).values_list('sound_id', flat=True)
                else:
                    sound_ids = SoundTags.objects.filter(tag_id=tag_id).values_list('sound_id', flat=True)
                query &= Q(id__in=sound_ids)
            except Tag.DoesNotExist:
                return Sound.objects.none()
        query &= Q(create_time__range=(start_datetime, end_datetime))
        query &= Q(category=category)

        if order == 'desc':
            sort_by = f'-{sort_by}'
        queryset = Sound.objects.filter(query).order_by(sort_by)

        return queryset

    @swagger_auto_schema(
        operation_description="分页查询满足条件的音频文件",
        manual_parameters=[
            openapi.Parameter('page', openapi.IN_QUERY, description="页码", type=openapi.TYPE_INTEGER, default=1),
            openapi.Parameter('page_size', openapi.IN_QUERY, description="每页条目数", type=openapi.TYPE_INTEGER, default=10),
            openapi.Parameter('start_datetime', openapi.IN_QUERY, description="开始时间 (格式: YYYY-MM-DDTHH:MM:SS)", type=openapi.TYPE_STRING),
            openapi.Parameter('end_datetime', openapi.IN_QUERY, description="结束时间 (格式: YYYY-MM-DDTHH:MM:SS)", type=openapi.TYPE_STRING),
            openapi.Parameter('category', openapi.IN_QUERY, description="音频分类 (SOUND: 普通音频, BKG: 背景音乐, EFFECT: 特效音)",
                              type=openapi.TYPE_STRING,
                              default='SOUND'),
            openapi.Parameter('tag_id', openapi.IN_QUERY, description="标签ID", type=openapi.TYPE_STRING),
            openapi.Parameter('sort_by', openapi.IN_QUERY, description="排序字段 (默认: create_time)", type=openapi.TYPE_STRING),
            openapi.Parameter('order', openapi.IN_QUERY, description="排序顺序 (asc 或 desc, 默认: asc)", type=openapi.TYPE_STRING),
        ],
        responses={200: SoundSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return ok_response(serializer.data)


class BindTagsToSoundAPIView(APIView):
    @swagger_auto_schema(
        operation_description="给音频绑定多个标签",
        request_body=SoundBindTagsSerializer,
        responses={
            200: "绑定成功",
            400: "无效的输入",
            404: "音频或标签不存在",
        },
    )
    def post(self, request):
        # 验证输入数据
        serializer = SoundBindTagsSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("无效的输入")

        sound_id = serializer.validated_data['sound_id']
        tag_ids = serializer.validated_data['tag_ids']

        # 检查音频是否存在
        if not Sound.objects.filter(id=sound_id).exists():
            return error_response("音频不存在")

        # 绑定标签
        for tag_id in tag_ids:
            # 检查标签是否存在（假设标签模型为 Tag）
            if not Tag.objects.filter(id=tag_id).exists():
                return error_response(f"标签id：{tag_id}不存在")

            # 创建 SoundTags 记录
            SoundTags.objects.create(sound_id=sound_id, tag_id=tag_id)

        return ok_response("绑定成功")


class DeleteSoundsAPIView(APIView):
    @swagger_auto_schema(
        operation_description="批量删除音频及其关联的标签记录",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'sound_ids': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_STRING, format='uuid'),
                    description='音频ID列表'
                ),
            },
            required=['sound_ids']
        ),
        responses={
            200: "删除成功",
            400: "无效的输入",
        },
    )
    def post(self, request):
        # 获取请求数据
        sound_ids = request.data.get('sound_ids')

        # 验证输入
        if not sound_ids or not isinstance(sound_ids, list):
            return error_response("输入参数错误，sound_ids必须是一个非空的列表")

        # 批量删除音频及其关联的标签记录
        try:
            # 删除关联的标签记录
            SoundTags.objects.filter(sound_id__in=sound_ids).delete()

            # 删除音频
            sounds = Sound.objects.filter(id__in=sound_ids)
            for sound in sounds:
                os.remove(os.path.join(SOUND_DIR.get(sound.category)) + sound.sound_path)
                sound.delete()

            return ok_response("删除成功")

        except Exception as e:
            return error_response(f"删除失败：{str(e)}")


class DeleteSoundTagAPIView(APIView):
    @swagger_auto_schema(
        operation_description="删除音频绑定的单个标签",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'sound_id': openapi.Schema(type=openapi.TYPE_STRING, format='uuid', description='音频ID'),
                'tag_id': openapi.Schema(type=openapi.TYPE_STRING, format='uuid', description='标签ID'),
            },
            required=['sound_id', 'tag_id']
        ),
        responses={
            200: "删除成功",
            404: "音频或标签绑定关系不存在",
        },
    )
    def post(self, request):
        # 获取请求数据
        sound_id = request.data.get('sound_id')
        tag_id = request.data.get('tag_id')

        if not sound_id or not tag_id:
            return error_response("sound_id 和 tag_id 不能为空")

        try:
            # 查找音频和标签的绑定关系
            sound_tag = SoundTags.objects.get(sound_id=sound_id, tag_id=tag_id)

            # 删除绑定关系
            sound_tag.delete()

            return ok_response("解绑成功")

        except SoundTags.DoesNotExist:
            return error_response("不存在绑定关系")


class SoundDetailView(generics.RetrieveAPIView):
    queryset = Sound.objects.all()
    serializer_class = SoundSerializer
    lookup_field = 'id'  # 根据 UUID 查找音频

    @swagger_auto_schema(
        operation_description="查看音频详情",
        responses={
            200: openapi.Response(
                description="音频详情",
                schema=SoundSerializer
            ),
            404: "音频不存在",
        }
    )
    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)


class SpeakerListAPIView(generics.ListAPIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = Speaker.objects.all()
    serializer_class = SpeakerSerializer

    def get_queryset(self):
        name = self.request.query_params.get('name')
        gender = self.request.query_params.get('gender')
        tag_ids = self.request.query_params.getlist('tag_ids')

        query = Q()
        if name:
            query &= Q(name__icontains=name)
        if gender:
            query &= Q(gender=gender)

        if tag_ids:
            try:
                speaker_tag_ids = []
                for tag_id in tag_ids:
                    tag = Tag.objects.get(id=tag_id)
                    if tag.parent == '':
                        child_tags = Tag.objects.filter(parent=tag_id).values_list('id', flat=True)
                        speaker_tag_ids.extend(child_tags)
                    else:
                        speaker_tag_ids.append(tag_id)

                speaker_ids = SpeakerTags.objects.filter(tag_id__in=speaker_tag_ids).values_list('speaker_id', flat=True)
                query &= Q(id__in=speaker_ids)
            except Tag.DoesNotExist:
                return Speaker.objects.none()
        queryset = Speaker.objects.filter(query).order_by('-create_time')

        return queryset

    @swagger_auto_schema(
        operation_description="分页查询满足条件的图片",
        manual_parameters=[
            openapi.Parameter('page', openapi.IN_QUERY, description="页码", type=openapi.TYPE_INTEGER, default=1),
            openapi.Parameter('page_size', openapi.IN_QUERY, description="每页条目数", type=openapi.TYPE_INTEGER,
                              default=10),
            openapi.Parameter('name', openapi.IN_QUERY, description="朗读者名称",
                              type=openapi.TYPE_STRING),
            openapi.Parameter('gender', openapi.IN_QUERY, description="性别",
                              type=openapi.TYPE_STRING),
            openapi.Parameter('tag_ids', openapi.IN_QUERY,
                              description="标签ID列表（使用tag_ids[]=id1&tag_ids[]=id2的形式传递）",
                              type=openapi.TYPE_ARRAY,
                              items=openapi.Items(type=openapi.TYPE_STRING),
                              collection_format='multi')
        ],
        responses={200: SpeakerSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return ok_response(serializer.data)


class RegenerateSoundAPIView(APIView):
    @swagger_auto_schema(
        operation_description="重新生成音频接口",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'sound_id': openapi.Schema(type=openapi.TYPE_STRING, format='uuid', description='音频ID'),
                'name': openapi.Schema(type=openapi.TYPE_STRING, description='音频名称'),
                'text': openapi.Schema(type=openapi.TYPE_STRING, description='文本'),
                'speaker_id': openapi.Schema(type=openapi.TYPE_STRING, description='音色'),

            },
            required=['sound_id', 'text', 'speaker_id']
        ),
        responses={
            200: "生成成功"
        },
    )
    def post(self, request):
        # 获取请求数据
        sound_id = request.data.get('sound_id')
        text = request.data.get('text')
        speaker_id = request.data.get('speaker_id')

        try:
            speaker = Speaker.objects.get(id=speaker_id)
            voice_seed = os.path.join(SEED_PATH, f"{speaker_id}.pt")
            old_sound = Sound.objects.get(id=sound_id)
            os.remove(os.path.join(SOUND_PATH, old_sound.sound_path))
            sound = Speech().chat_tts(text, speaker, voice_seed)
            old_sound.delete()
            old_sound.sound_path = sound.sound_path
            old_sound.desc = text
            old_spec = old_sound.spec
            old_spec['speaker'] = speaker
            old_spec.spec = old_spec
            old_sound.save()

            return ok_response("重新生成音频成功")

        except Exception:
            return error_response("重新生成音频失败")


class GenerateSoundAPIView(APIView):
    @swagger_auto_schema(
        operation_description="生成音频接口",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'text': openapi.Schema(type=openapi.TYPE_STRING, description='文本'),
                'speaker_id': openapi.Schema(type=openapi.TYPE_STRING, description='音色'),

            },
            required=['text', 'speaker_id']
        ),
        responses={
            200: "生成成功"
        },
    )
    def post(self, request):
        # 获取请求数据
        text = request.data.get('text')
        speaker_id = request.data.get('speaker_id')

        try:
            speaker = Speaker.objects.get(id=speaker_id)
            voice_seed = os.path.join(SEED_PATH, f"{speaker_id}.pt")

            sound = Speech().chat_tts(text, speaker, voice_seed)
            sound.save()
            return ok_response("生成音频成功")

        except Exception:
            return error_response("生成音频失败")


class SpeakerCreateAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="创建朗读者",
        request_body=SpeakerSerializer,
        responses={
            201: openapi.Response(
                description="创建成功",
                schema=SpeakerSerializer
            ),
            400: "无效的输入"
        }
    )
    def post(self, request):
        try:

            speaker_name = request.data.get('name')
            gender = request.data.get('gender')
            tags = request.data.get('tags', [])
            voice_style_file = request.FILES.get('voice_style_file')
            if not voice_style_file:
                return error_response("未提供音色文件")
            else:

                speaker_id = str(uuid.uuid4())
                file_path = os.path.join(SEED_PATH, f"{speaker_id}.pt")
                with open(file_path, 'wb+') as destination:
                    for chunk in voice_style_file.chunks():
                        destination.write(chunk)

                for tag in tags:
                    if not Tag.objects.filter(id=tag, category='SPEAKER').exists():
                        return error_response(f"标签id：{tag}不存在")
                    else:
                        SpeakerTags.objects.create(speaker_id=speaker_id, tag_id=tag)

                Speaker.objects.create(id=speaker_id, name=speaker_name, gender=gender, sample=DEFAULT_SAMPLE_TEXT)

                return ok_response("创建成功")
        except Exception as e:
            return error_response(f"创建失败: {str(e)}")


class DeleteSpeakerAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="删除朗读者及其关联的标签记录",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'speaker_id': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format='uuid',
                    description='朗读者ID'
                ),
            },
            required=['speaker_id']
        ),
        responses={
            200: "删除成功",
            404: "朗读者不存在",
        }
    )
    def post(self, request):
        speaker_id = request.data.get('speaker_id')
        if not speaker_id:
            return error_response("speaker_id不能为空")

        try:
            # 删除关联的标签记录
            SpeakerTags.objects.filter(speaker_id=speaker_id).delete()

            # 删除朗读者
            speaker = Speaker.objects.get(id=speaker_id)

            if os.path.exists(os.path.join(SEED_PATH, f"{speaker_id}.pt")):
                os.remove(os.path.join(SEED_PATH, f"{speaker_id}.pt"))
            speaker.delete()

            return ok_response("删除成功")
        except Speaker.DoesNotExist:
            return error_response("朗读者不存在")
        except Exception as e:
            return error_response(f"删除失败: {str(e)}")


class UpdateSpeakerAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="更新朗读者信息",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'speaker_id': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format='uuid',
                    description='朗读者ID'
                ),
                'name': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='朗读者名称'
                ),
                'gender': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='性别',
                    enum=['MALE', 'FEMALE']
                ),
                'voice_style_file': openapi.Schema(
                    type=openapi.TYPE_FILE,
                    description='音色种子文件'
                ),
                'tag_ids': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_STRING, format='uuid'),
                    description='新的标签ID列表'
                ),
                'sample': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='试听文本'
                )
            },
            required=['speaker_id']
        ),
        responses={
            200: "更新成功",
            400: "无效的输入",
            404: "朗读者不存在"
        }
    )
    def post(self, request):
        speaker_id = request.data.get('speaker_id')
        name = request.data.get('name')
        gender = request.data.get('gender')
        voice_style_file = request.FILES.get('voice_style_file')
        tag_ids = request.data.get('tag_ids', [])
        sample = request.data.get('sample')

        if not speaker_id:
            return error_response("speaker_id不能为空")

        try:
            # 获取朗读者
            speaker = Speaker.objects.get(id=speaker_id)

            # 更新基本信息
            if name:
                speaker.name = name
            if gender:
                speaker.gender = gender
            if sample:
                speaker.sample = sample

            # 更新音色文件
            if voice_style_file:
                file_path = os.path.join(SEED_PATH, f"{speaker_id}.pt")
                with open(file_path, 'wb+') as destination:
                    for chunk in voice_style_file.chunks():
                        destination.write(chunk)

            # 更新标签
            if tag_ids:
                if not isinstance(tag_ids, list):
                    return error_response("tag_ids必须是列表")

                # 检查所有标签是否存在
                for tag_id in tag_ids:
                    if not Tag.objects.filter(id=tag_id, category='SPEAKER').exists():
                        return error_response(f"标签id：{tag_id}不存在或不属于SPEAKER类别")

                # 删除原有所有标签
                SpeakerTags.objects.filter(speaker_id=speaker_id).delete()

                # 绑定新的标签
                for tag_id in tag_ids:
                    SpeakerTags.objects.create(speaker_id=speaker_id, tag_id=tag_id)

            speaker.save()
            return ok_response("更新成功")

        except Speaker.DoesNotExist:
            return error_response("朗读者不存在")
        except Exception as e:
            return error_response(f"更新失败: {str(e)}")
