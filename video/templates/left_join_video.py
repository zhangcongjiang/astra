import logging
import os.path
import uuid

from astra.settings import VIDEO_PATH
from video.templates.video_template import VideoTemplate, InputType, VideoOrientation
from moviepy.editor import ImageClip, CompositeVideoClip
from moviepy.video.fx.all import resize
import numpy as np
logger = logging.getLogger("video")


class NbaHistory(VideoTemplate):

    def __init__(self):
        super().__init__()
        self.template_id = str(uuid.uuid3(uuid.NAMESPACE_DNS, self.__class__.__name__))
        self.name = '模板视频（1）'
        self.desc = '图片翻页生成视频'
        self.parameters = {
            "视频模板ID": {
                "type": InputType.STRING,
                "key": "template_id",
            },
            "标题": {
                "type": InputType.TEXT,
                "key": "title",
                "max": 30,
                "min": 4
            },
            "封面图片": {
                "type": InputType.SELECT,
                "key": "cover_img",
                "value": "BackgroundImageList"
            },
            "默认音色": {
                "type": InputType.SELECT,
                "key": "speaker",
                "value": "SpeakerList"
            },
            "背景音乐": {
                "type": InputType.SELECT,
                "key": "bgm",
                "value": "BgmList"
            },
            "开场部分": {
                "type": InputType.OBJECT,
                "key": "opening",             
                "value": {
                    '文本': {
                        "type": InputType.TEXT,
                        "key": "text",
                        "max": 0,
                        "min": 0
                    },
                    '图片列表': {
                        "type": InputType.SELECTLIST,
                        "key": "image_list",
                        "value": "NormalImageList", 
                    },
                    "音色": {
                        "type": InputType.SELECT,
                        "key": "speaker",
                        "value": "SpeakerList",
                        "default": True,
                        "allow_edit": False
                    },
                    "特效音": {
                        "type": InputType.SELECT,
                        "key": "effect",
                        "value": "EffectList",
                        "required": False
                    }

                }
            },
            "视频主体": {
                "type": InputType.OBJECT_LIST,
                "key": "content",
                "value": {
                    '文本': {
                        "type": InputType.TEXT,
                        "key": "text",
                        "max": 0,
                        "min": 0
                    },
                    '图片列表': {
                        "type": InputType.SELECTLIST,
                        "key": "image_list",
                        "value": "NormalImageList"
                    },
                    "音色": {
                        "type": InputType.SELECT,
                        "key": "speaker",
                        "value": "SpeakerList",
                        "default": True,
                        "allow_edit": False
                    },
                    "特效音": {
                        "type": InputType.SELECT,
                        "key": "effect",
                        "value": "EffectList",
                        "required": False
                    }
                }
            }
        }
        self.orientation = VideoOrientation.HORIZONTAL.name
        self.demo = os.path.join(VIDEO_PATH, f"{self.template_id}.mp4")

    def process(self, video_id, parameters):
        """实现多张图片向左滑动进入并停留在视频中央的视频效果
        
        Args:
            video_id: 视频唯一ID
            parameters: 包含图片路径列表的参数
        """
        # 获取图片列表
        image_paths = parameters.get('图片列表', [])
        if not image_paths:
            raise ValueError("未提供图片列表")
            
        # 视频参数
        duration_per_image = 6  # 每张图片总时长(5秒停留+0.5秒进入+0.5秒退出)
        fps = 24
        screen_width, screen_height = 1920, 1080  # 假设横版视频
        
        clips = []
        
        for i, img_path in enumerate(image_paths):
            # 创建图片剪辑
            img_clip = ImageClip(img_path, duration=duration_per_image)
            
            # 调整图片大小以适应屏幕
            img_clip = resize(img_clip, height=screen_height*0.8)
            
            # 计算图片宽度和位置
            img_width = img_clip.w
            start_pos = (screen_width, (screen_height - img_clip.h)/2)  # 从右侧进入
            end_pos = ((screen_width - img_width)/2, (screen_height - img_clip.h)/2)  # 中央位置
            
            # 定义动画函数
            def make_frame(t):
                if t < 0.5:  # 进入动画
                    x = start_pos[0] + (end_pos[0] - start_pos[0]) * (t/0.5)
                    return img_clip.get_frame(t).set_position((x, end_pos[1]))
                elif t < 5.5:  # 停留
                    return img_clip.get_frame(t).set_position(end_pos)
                else:  # 退出动画
                    x = end_pos[0] + (start_pos[0] - end_pos[0]) * ((t-5.5)/0.5)
                    return img_clip.get_frame(t).set_position((x, end_pos[1]))
            
            # 创建动画剪辑
            animated_clip = img_clip.fl(make_frame, apply_to=['mask'])
            
            # 设置剪辑的开始时间(上一张开始退出时下一张开始进入)
            start_time = i * (duration_per_image - 0.5)
            animated_clip = animated_clip.set_start(start_time)
            
            clips.append(animated_clip)
        
        # 计算总时长
        total_duration = (len(image_paths) - 1) * (duration_per_image - 0.5) + duration_per_image
        
        # 创建合成视频
        final_clip = CompositeVideoClip(clips, size=(screen_width, screen_height))
        final_clip = final_clip.set_duration(total_duration)
        
        # 输出视频文件
        output_path = os.path.join(VIDEO_PATH, f"{video_id}.mp4")
        final_clip.write_videofile(output_path, fps=fps)
        
        return output_path

    def calc_start_time(self, total_time, img_num):
        x = round(2 * (total_time - 0.2 * img_num) / (img_num * (img_num + 1)), 2)

        return [0.2 + i * x for i in range(1, img_num + 1)]
