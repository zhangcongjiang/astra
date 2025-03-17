import glob
import logging
import os
import uuid
import zipfile
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
from io import BytesIO

from pydub import AudioSegment

from astra import settings
from astra.settings import FONTS_PATH, SOUND_PATH, MOVIE_PATH, IMG_PATH, FFMPEG_PATH, BGM_PATH
from common.exceptions import BusinessException
from common.redis_tools import ControlRedis
from video.models import Parameters
from proglog import ProgressBarLogger

logger = logging.getLogger("video")


class VideoOrientation(Enum):
    HORIZONTAL = 0  # 横版视频
    VERTICAL = 1  # 竖版视频


class VideoTemplate:
    def __init__(self):
        self.ffmpeg_path = FFMPEG_PATH
        self.img_path = IMG_PATH
        self.sound_path = SOUND_PATH
        self.movie_path = MOVIE_PATH
        self.bgm_path = BGM_PATH
        self.font = os.path.join(FONTS_PATH, 'STXINWEI.TTF')
        self.name = ''
        self.desc = ''
        self.frame_rate = 20
        self.orientation = VideoOrientation.HORIZONTAL.name
        self.parameters = {}

        self.templates = []
        self.methods = {}
        self.executor = ThreadPoolExecutor(max_workers=8)
        self.set_ffmpeg_path()

        # redis 记录视频生成进度
        self.redis_control = ControlRedis()

    def set_ffmpeg_path(self):
        os.environ["PATH"] += os.pathsep + os.path.dirname(self.ffmpeg_path)
        AudioSegment.converter = self.ffmpeg_path

    def generate_video(self, parameters):
        template_id = parameters.get('template_id')
        if template_id not in self.methods.keys():
            return 'Method not found'
        video_id = str(uuid.uuid4())
        logger.info("生成视频封面完成")
        self.executor.submit(self.methods[template_id]().process, video_id, parameters)
        return {
            'video_id': video_id,
            'parameters': parameters
        }

    def get_templates(self):
        subclasses = VideoTemplate.__subclasses__()

        for subclass in subclasses:
            # 创建子类实例
            instance = subclass()
            template_id = str(uuid.uuid3(uuid.NAMESPACE_DNS, subclass.__name__))
            if template_id not in self.methods.keys():
                template_info = {
                    "template_id": template_id,
                    "name": instance.name,
                    "desc": instance.desc,
                    "parameters": instance.parameters,
                    "orientation": instance.orientation
                }
                self.templates.append(template_info)
                logger.info(f"register {instance.name}，info: {template_info}")
                self.methods[template_id] = subclass
        return self.templates

    @staticmethod
    def download(video_id):
        from video.models import Video
        video = Video.objects.get(video_id=video_id)
        if not video.result:
            logger.error("视频生成失败，请重新生成")
            raise BusinessException("视频生成失败，请重新生成")
        else:
            video_filename = f'{video_id}.mp4'
            image1_filename = f'{video_id}.png'

            video_path = os.path.join(settings.MOVIE_PATH, video_filename)
            image1_path = os.path.join(settings.IMG_PATH, image1_filename)

            # 创建一个字节流对象用于存储ZIP文件
            zip_buffer = BytesIO()

            # 创建ZIP文件
            with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
                zip_file.write(video_path, video_filename)
                zip_file.write(image1_path, image1_filename)

            # 设置ZIP文件指针回到开始
            zip_buffer.seek(0)
            logger.info(f"视频{video_id}下载成功")
            return zip_buffer

    def clear_temps(self, video_id):
        # 构建搜索模式
        search_pattern = os.path.join(self.sound_path, f"{video_id}*")

        # 获取所有匹配的文件
        files_to_delete = glob.glob(search_pattern)

        # 删除每个文件
        for file_path in files_to_delete:
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"Failed to delete {file_path}: {e}")
        print("临时音频文件删除完成")

    @staticmethod
    def save_parameters(data):
        param_id = str(uuid.uuid4())
        data["param_id"] = param_id
        Parameters(**data).save()
        return param_id

    @staticmethod
    def get_size(orientation):
        if orientation == VideoOrientation.HORIZONTAL.name:
            return 1920, 1080
        elif orientation == VideoOrientation.VERTICAL.name:
            return 1080, 1920
        else:
            logger.error(f"视频类型异常，{orientation}")


class MyBarLogger(ProgressBarLogger):
    def __init__(self, video_id):
        super().__init__()
        self.video_id = video_id
        self.redis = ControlRedis()

    def bars_callback(self, bar, attr, value, old_value=None):
        # Every time the logger progress is updated, this function is called
        percentage = (value / self.bars[bar]['total']) * 100
        self.redis.set_key(self.video_id, round(percentage, 2))
