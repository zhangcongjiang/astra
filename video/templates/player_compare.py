import logging
import os
import traceback
import uuid

import numpy as np
from PIL import Image as PilImage, ImageDraw, ImageFont
from moviepy import *

from astra.settings import VIDEO_PATH, LOGO_PATH
from video.models import Video
from video.templates.video_template import VideoTemplate, VideoOrientation
from voice.models import Sound

logger = logging.getLogger("video")


class PlayerCompare(VideoTemplate):

    def __init__(self):
        super().__init__()
        self.template_id = str(uuid.uuid3(uuid.NAMESPACE_DNS, self.__class__.__name__))
        self.name = '数据对比生成视频'
        self.desc = '通过两组数据对比，结合背景音乐和部分图片，生成视频'
        self.parameters = {
            'form': [

                {
                    'name': 'title',
                    'label': '视频标题',
                    'type': 'input',
                    'inputType': 'text',
                    'required': True,
                    'placeholder': '请输入视频的标题'
                },
                {
                    'name': 'reader',
                    'label': '选择配音员',
                    'type': 'select',
                    'required': False,
                    'options': {
                        'source': 'remote',
                        'url': '/voice/speakers/select/',
                        'valueKey': 'id',
                        'labelKey': 'name'
                    },
                    'description': '选择一个AI配音员来朗读文案。'
                },
                {
                    'name': 'bgm',
                    'label': '背景音乐',
                    'type': 'select',
                    'required': True,
                    'options': {
                        'source': 'server',
                        'resourceType': 'audio'
                    },
                    'description': '从您的媒体库中选择一首背景音乐。'
                },
                {
                    'name': 'start_text',
                    'label': '开场文案',
                    'type': 'textarea',
                    'rows': 3,
                    'required': True,
                    'placeholder': '请输入视频的开场白。'
                },
                {
                    'name': 'main',
                    'label': '主要比较者',
                    'type': 'group',
                    'replicable': False,
                    'fields': [{
                        'name': 'avatar',
                        'label': '头像',
                        'type': 'select',
                        'multiple': False,
                        'required': True,
                        'options': {
                            'source': 'server',
                            'resourceType': 'image'
                        }

                    },
                        {
                            'name': 'body',
                            'label': '全身照',
                            'type': 'select',
                            'multiple': False,
                            'required': True,
                            'options': {
                                'source': 'server',
                                'resourceType': 'image'
                            }
                        },
                        {
                            'name': 'name',
                            'label': '姓名',
                            'type': 'textarea',
                            'rows': 3,
                            'required': True,
                            'placeholder': '请输入主要比较者名称。'
                        },
                        {
                            'name': 'draft',
                            'label': '选秀顺位',
                            'type': 'textarea',
                            'rows': 3,
                            'required': True,
                            'placeholder': '请输入选秀顺位。'
                        },
                        {
                            'name': 'game_result',
                            'label': '战绩',
                            'type': 'textarea',
                            'rows': 3,
                            'required': True,
                            'placeholder': '请输入战绩。'
                        },
                        {
                            'name': 'data',
                            'label': '数据',
                            'type': 'textarea',
                            'rows': 3,
                            'required': True,
                            'placeholder': '请输入数据。'
                        }
                    ]
                },
                {
                    'name': 'compared',
                    'label': '被比较者',
                    'type': 'group',
                    'replicable': False,
                    'fields': [{
                        'name': 'avatar',
                        'label': '头像',
                        'type': 'select',
                        'multiple': False,
                        'required': True,
                        'options': {
                            'source': 'server',
                            'resourceType': 'image'
                        }

                    },
                        {
                            'name': 'body',
                            'label': '全身照',
                            'type': 'select',
                            'multiple': False,
                            'required': True,
                            'options': {
                                'source': 'server',
                                'resourceType': 'image'
                            }
                        },
                        {
                            'name': 'name',
                            'label': '姓名',
                            'type': 'textarea',
                            'rows': 3,
                            'required': True,
                            'placeholder': '请输入被比较者名称。'
                        },
                        {
                            'name': 'draft',
                            'label': '选秀顺位',
                            'type': 'textarea',
                            'rows': 3,
                            'required': True,
                            'placeholder': '请输入选秀顺位。'
                        },
                        {
                            'name': 'game_result',
                            'label': '战绩',
                            'type': 'textarea',
                            'rows': 3,
                            'required': True,
                            'placeholder': '请输入战绩。'
                        },
                        {
                            'name': 'data',
                            'label': '数据',
                            'type': 'textarea',
                            'rows': 3,
                            'required': True,
                            'placeholder': '请输入数据。'
                        }
                    ]
                },
                {
                    'name': 'content',
                    'label': '文案内容',
                    'type': 'textarea',
                    'rows': 3,
                    'required': False,
                    'placeholder': '请输入视频文案。'
                }
            ]
        }
        self.orientation = VideoOrientation.VERTICAL.name
        self.demo = "/media/videos/player_compare.mp4"
        self.default_speaker = None
        self.width, self.height = self.get_size(self.orientation)
        self.duration_start = 0
        self.cover = None
        self.video_type = 'Regular'
        self.temp_files = []

    def process(self, user, video_id, parameters):
        """实现带字幕和音频同步的视频生成

        Args:
            video_id: 视频唯一ID
            parameters: 包含图片路径列表和文本的参数
            :param user: 创建者
        """
        logger.info(f"视频生成请求参数：{parameters}")
        project_name = parameters.get('title')
        param_id = self.save_parameters(self.template_id, user, project_name, parameters)

        # 获取开场部分和视频主体内容
        start_text = parameters.get('start_text', '')
        # end = parameters.get('end', {})
        bgm = parameters.get('bgm')  # 获取背景音乐路径
        content = parameters.get('content')
        main_data = parameters.get('main', {})
        compared_data = parameters.get('compared', {})
        main_avatar_path = main_data['avatar']
        compared_avatar_path = compared_data['avatar']
        main_body_path = main_data['body']
        compared_body_path = compared_data['body']

        output_path = os.path.join(VIDEO_PATH, f"{video_id}.mp4")
        logo_path = os.path.join(LOGO_PATH, 'logo.png')
        reader = parameters.get('reader')
        self.default_speaker = reader

        Video(creator=user, title=f"{main_data.get('name')}vs{compared_data.get('name')}{project_name}", content=content, video_type=self.video_type,
              result='Process',
              process=0.0, id=video_id, param_id=param_id).save()
        try:

            # 调整图片尺寸
            self.resize_images_for_vertical(
                main_avatar_path, compared_avatar_path,
                main_body_path, compared_body_path, logo_path
            )
            tts = self.speech.chat_tts(start_text, reader, user, video_id)
            Video.objects.filter(id=video_id).update(process=0.2)
            tts_file = os.path.join(self.tts_path, f'{tts.id}.wav')

            data = {
                "main": {
                    "name": main_data.get('name'),
                    "draft": main_data.get('draft'),
                    "game_result": main_data.get('game_result'),
                    "data": main_data.get('data')
                },
                "compared": {
                    "name": compared_data.get('name'),
                    "draft": compared_data.get('draft'),
                    "game_result": compared_data.get('game_result'),
                    "data": compared_data.get('data')
                }

            }
            bgm_sound = Sound.objects.get(id=bgm)
            self.create_video_with_effects(project_name,
                                           self.temp_files[0], self.temp_files[1],
                                           self.temp_files[2], self.temp_files[3],
                                           output_path, data,
                                           tts_file,  # 键盘音效路径
                                           os.path.join(self.sound_path, bgm_sound.sound_path)  # 背景音乐路径
                                           )
            Video.objects.filter(id=video_id).update(result='Success', process=1.0, video_path=f"/media/videos/{video_id}.mp4")
        except Exception as e:
            logger.error(traceback.format_exc())
            Video.objects.filter(id=video_id).update(result='Fail')
            if os.path.exists(output_path):
                os.remove(output_path)
            raise e
        finally:
            for file in self.temp_files:
                if os.path.exists(file):
                    os.remove(file)

    def create_deal_animation(self, img_path, final_position, final_size, start_time, duration, total_duration):
        """
        创建类似“发牌”的动画：图片从右上角快速飞到指定位置
        """
        # 使用PIL加载并调整图片尺寸
        pil_img = PilImage.open(img_path).convert("RGBA")

        if final_size:
            pil_img = pil_img.resize(final_size, PilImage.LANCZOS)

        # 转为 numpy 数组并创建 ImageClip
        img_array = np.array(pil_img)
        img = ImageClip(img_array).with_duration(total_duration)

        # 起始位置（右上角飞入）
        start_pos = (900, -img.h)

        # 位置动画
        def position_func(t):
            if t < start_time:  # 还没开始飞
                return start_pos
            elif start_time <= t < start_time + duration:
                linear_progress = (t - start_time) / duration
                progress = 1 - (1 - linear_progress) ** 2  # ease-out
                x = start_pos[0] + (final_position[0] - start_pos[0]) * progress
                y = start_pos[1] + (final_position[1] - start_pos[1]) * progress
                return (x, y)
            else:  # 到达目标位置
                return final_position

        return img.with_position(position_func)

    def create_name_typewriter_effect(self, data, font_path, font_size, start_time, total_duration):
        """
        创建球员姓名打字机效果
        """

        def make_frame(t):
            img = PilImage.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)

            # 只在开始时间后才显示
            if t >= start_time:
                main = data.get('main')
                compared = data.get('compared')

                # 使用粗体字体
                bold_font = ImageFont.truetype(font_path, font_size + 4)

                # 计算当前应该显示的文字长度
                progress = min(1, (t - start_time) / 1)  # 名字打字效果持续1秒（你可以调整）

                # 主球员名字打字效果
                main_name = main.get('name')
                main_chars_to_show = int(len(main_name) * progress)
                current_main_text = main_name[:main_chars_to_show]
                main_mask = bold_font.getmask(current_main_text)
                draw.text((225 - int(main_mask.size[0]) / 2, 365), text=current_main_text, font=bold_font, fill='red')

                # 对比球员名字打字效果
                compared_name = compared.get('name')
                compared_chars_to_show = int(len(compared_name) * progress)
                current_compared_text = compared_name[:compared_chars_to_show]
                compared_mask = bold_font.getmask(current_compared_text)
                draw.text((675 - int(compared_mask.size[0]) / 2, 365), text=current_compared_text, font=bold_font, fill='yellow')

            return np.array(img)

        return VideoClip(make_frame, duration=total_duration)

    # 创建打字机效果，并在完成后保持显示
    def create_typewriter_effect(self, text, font_path, font_size, position, duration, total_duration, bg_points=None):
        """
        创建打字机效果，并在完成后保持显示
        """

        # 创建临时函数来生成每一帧
        def make_frame(t):
            # 创建新的图像
            img = PilImage.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)

            # 绘制梯形背景（如果提供了背景点）
            if bg_points:
                draw.polygon(bg_points, fill="#1a3365")

            # 计算当前应该显示的文字长度
            if t < duration:
                progress = min(1, t / duration)
                chars_to_show = int(len(text) * progress)
                current_text = text[:chars_to_show]
            else:
                current_text = text  # 动画完成后显示完整文字

            # 绘制文字
            font = ImageFont.truetype(font_path, font_size)
            draw.text(position, current_text, font=font, fill="yellow")

            return np.array(img)

        return VideoClip(make_frame, duration=total_duration)

    # 创建静态梯形背景
    def create_static_background(self, bg_points, total_duration):
        """
        创建静态梯形背景
        """

        def make_frame(t):
            img = PilImage.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.polygon(bg_points, fill="#1a3365")
            return np.array(img)

        return VideoClip(make_frame, duration=total_duration)

    # 创建球员信息显示效果（在所有图片到达后显示）
    def create_player_info_effect(self, data, font_path, font_size, start_time, total_duration):
        """
        创建球员信息显示效果
        """
        text_font = ImageFont.truetype(font_path, font_size)
        background_color = '#ffffff'

        def make_frame(t):
            img = PilImage.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)

            # 只在开始时间后才显示
            if t >= start_time:
                main = data.get('main')
                compared = data.get('compared')

                # 绘制选秀信息
                main_draft = main.get('draft')
                compared_draft = compared.get('draft')
                draw.text((225 - int(text_font.getmask(main_draft).size[0]) / 2, 420), text=main_draft, font=text_font, fill=background_color)
                draw.text((675 - int(text_font.getmask(compared_draft).size[0]) / 2, 420), text=compared_draft, font=text_font, fill=background_color)

                # 绘制比赛结果
                main_game_result = main.get('game_result')
                compared_game_result = compared.get('game_result')
                draw.text((225 - int(text_font.getmask(main_game_result).size[0]) / 2, 455), text=main_game_result, font=text_font,
                          fill=background_color)
                draw.text((675 - int(text_font.getmask(compared_game_result).size[0]) / 2, 455), text=compared_game_result, font=text_font,
                          fill=background_color)

                line_y = 500  # 横线位置，在头像和信息下方
                draw.line([(30, line_y), (870, line_y)], fill=background_color, width=2)

            return np.array(img)

        return VideoClip(make_frame, duration=total_duration)

    def create_wipe_effect(self, img_path, pos, start_time, duration, video_duration):
        img_clip = ImageClip(img_path).with_duration(video_duration - start_time)
        w, h = img_clip.size

        # 动态 mask
        def make_mask_frame(t):
            mask = np.zeros((h, w), dtype=np.float32)
            progress = min(1.0, max(0.0, t / duration))
            visible_width = int(progress * w)
            mask[:, :visible_width] = 1.0
            return mask

        anim_mask = VideoClip(make_mask_frame, duration=duration)

        # 后半段全亮 mask
        def full_mask_frame(t):
            return np.ones((h, w), dtype=np.float32)

        full_mask = VideoClip(full_mask_frame, duration=(video_duration - start_time - duration))

        # 拼接 mask
        final_mask = concatenate_videoclips([anim_mask, full_mask])

        # 绑定 mask
        img_clip = img_clip.with_mask(final_mask).with_position(pos).with_start(start_time)

        return img_clip

    def create_data_comparison_effect(self, data, font_path, font_size, start_time, total_duration):
        """
        创建数据对比效果：
        - 左边的数据槽从右往左填充
        - 右边的数据槽从左往右填充
        - 类型文字在动画过程中为红色，结束后为白色
        - 数据数值从0逐渐增加到最终值
        - 进度条由浅到深渐变，结束时更好的一方为红色
        - 更好的一方数值最终显示为红色
        """
        text_font = ImageFont.truetype(font_path, font_size)
        data_font = ImageFont.truetype(font_path, 24)
        background_color = '#ffffff'

        # 基础颜色
        left_base_light = (128, 0, 0, 192)  # 浅红
        left_base_dark = (255, 0, 0, 192)  # 深红（最终色）

        right_base_light = (255, 255, 128, 192)  # 浅黄
        right_base_dark = (255, 255, 0, 192)  # 深黄（最终色）

        # 数据槽位置参数
        bar_y_start = 540
        bar_height = 40
        bar_spacing = 60
        left_bar_x1, left_bar_x2 = 90, 380
        right_bar_x1, right_bar_x2 = 520, 810

        left_total = left_bar_x2 - left_bar_x1
        right_total = right_bar_x2 - right_bar_x1

        main_data = data['main']['data']
        compared_data = data['compared']['data']
        data_items = list(main_data.keys())

        percent_items = ['投篮', '三分球', '罚球', '胜率']
        int_items = ['出战场次']
        negative_items = ['失误']  # 数值越大越差的指标

        def fmt_value(item, v):
            if item in percent_items:
                return f"{round(v, 1)}%" if isinstance(v, float) else f"{v}%"
            elif item in int_items:
                return f"{int(v)}"
            else:
                return f"{round(v, 1)}" if isinstance(v, float) else f"{v}"

        def lerp_color(c1, c2, p):
            """颜色插值：从c1渐变到c2"""
            return tuple(int(c1[i] + (c2[i] - c1[i]) * p) for i in range(4))

        def draw_left_bar(img, bar_y, fill_w, color):
            if fill_w <= 0:
                return
            left = left_bar_x2 - fill_w
            layer = PilImage.new('RGBA', (fill_w, bar_height), color)
            img.paste(layer, (left, bar_y), layer)

        def draw_right_bar(img, bar_y, fill_w, color):
            if fill_w <= 0:
                return
            layer = PilImage.new('RGBA', (fill_w, bar_height), color)
            img.paste(layer, (right_bar_x1, bar_y), layer)

        def make_frame(t):
            img = PilImage.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)

            if t >= start_time:
                elapsed_time = t - start_time

                for i, item in enumerate(data_items):
                    bar_y = bar_y_start + i * bar_spacing
                    item_start_time = i * 2.5

                    if elapsed_time < item_start_time:
                        continue

                    # 计算阶段进度
                    if elapsed_time < item_start_time + 2.5:
                        progress = min(1, (elapsed_time - item_start_time) / 2.5)
                    else:
                        progress = 1.0

                    # 类型文字颜色
                    label_color = (255, 0, 0, 255) if progress < 1 else background_color
                    label_width = text_font.getmask(item).size[0]
                    label_x = 450 - label_width / 2
                    draw.text((label_x, bar_y + (bar_height - 24) // 2),
                              text=item, font=text_font, fill=label_color)

                    # 边框
                    draw.rectangle([left_bar_x1, bar_y, left_bar_x2, bar_y + bar_height], outline=background_color, width=1)
                    draw.rectangle([right_bar_x1, bar_y, right_bar_x2, bar_y + bar_height], outline=background_color, width=1)

                    main_value = main_data[item]
                    compared_value = compared_data[item]

                    # 判断哪边更好
                    if item in negative_items:
                        better_side = "right" if main_value > compared_value else "left" if compared_value > main_value else "equal"
                    else:
                        better_side = "left" if main_value > compared_value else "right" if compared_value > main_value else "equal"

                    # 目标宽度
                    if main_value == compared_value:
                        left_target = left_total
                        right_target = right_total
                    elif main_value > compared_value:
                        left_target = left_total
                        right_target = int(right_total * (compared_value / main_value)) if main_value != 0 else 0
                    else:
                        right_target = right_total
                        left_target = int(left_total * (main_value / compared_value)) if compared_value != 0 else 0

                    left_current = int(left_target * progress)
                    right_current = int(right_target * progress)

                    # 同步渐变颜色（浅 → 深）
                    left_bar_color = lerp_color(left_base_light, left_base_dark, progress)
                    right_bar_color = lerp_color(right_base_light, right_base_dark, progress)

                    # 左右条绘制
                    draw_left_bar(img, bar_y, left_current, left_bar_color)
                    draw_right_bar(img, bar_y, right_current, right_bar_color)

                    # 数据文字随进度变化
                    main_current = main_value * progress
                    compared_current = compared_value * progress

                    main_data_text = fmt_value(item, main_current)
                    compared_data_text = fmt_value(item, compared_current)

                    # 默认白色，结束时优胜方红色
                    main_color = background_color
                    compared_color = background_color
                    if progress == 1:
                        if better_side == "left":
                            main_color = (255, 0, 0, 255)
                        elif better_side == "right":
                            compared_color = (255, 255, 0, 255)

                    draw.text((left_bar_x1 - data_font.getmask(main_data_text).size[0] - 5,
                               bar_y + (bar_height - 20) // 2),
                              text=main_data_text, font=data_font, fill=main_color)

                    draw.text((right_bar_x2 + 5,
                               bar_y + (bar_height - 20) // 2),
                              text=compared_data_text, font=data_font, fill=compared_color)

            return np.array(img)

        return VideoClip(make_frame, duration=total_duration)

    # 主函数
    def create_video_with_effects(self, title, main_avatar_path, compared_avatar_path, main_body_path, compared_body_path, output_path, data,
                                  keyboard_sound_path,
                                  bg_music_path):
        # 竖版视频尺寸
        video_size = (self.width, self.height)

        # 设置持续时间
        total_duration = 40  # 总时长延长到30秒，因为数据对比需要时间
        animation_duration = 2  # 动画效果时长2秒
        info_start_time = 2  # 球员信息在第2.5秒开始显示
        data_start_time = 5.0  # 数据对比在第5秒开始显示

        # 计算标题文本尺寸和梯形背景
        title_font = ImageFont.truetype('STXINWEI.TTF', 36)
        title_mask = title_font.getmask(title)
        title_width = title_mask.size[0]
        title_height = title_mask.size[1]
        title_x = 450 - title_width / 2
        title_y = 20

        # 计算梯形四个点的坐标
        bg_top_width = title_width + 100
        bg_bottom_width = title_width + 40
        bg_height = title_height + 20

        bg_points = [
            (450 - bg_top_width / 2, title_y - 20),
            (450 + bg_top_width / 2, title_y - 20),
            (450 + bg_bottom_width / 2, title_y + bg_height - 10),
            (450 - bg_bottom_width / 2, title_y + bg_height - 10)
        ]

        # 创建静态梯形背景（全程显示）
        static_bg_clip = self.create_static_background(bg_points, total_duration)

        # 创建打字机效果（和图片动画同时开始）
        typewriter_clip = self.create_typewriter_effect(
            text=title,
            font_path='STXINWEI.TTF',
            font_size=36,
            position=(title_x, title_y),
            duration=animation_duration,
            total_duration=total_duration,
            bg_points=None
        )

        # 创建球员信息显示效果
        player_info_clip = self.create_player_info_effect(
            data=data,
            font_path='STXINWEI.TTF',
            font_size=28,
            start_time=info_start_time + 1,
            total_duration=total_duration
        )

        wipe_clip = self.create_wipe_effect(
            img_path=os.path.join(LOGO_PATH, 'vs.png'),
            pos=(369, 120),
            start_time=info_start_time + 1,
            duration=0.5,
            video_duration=total_duration  # 整个视频时长
        )

        # 创建球员姓名打字机效果
        name_typewriter_clip = self.create_name_typewriter_effect(
            data=data,
            font_path='STXINWEI.TTF',
            font_size=36,
            start_time=info_start_time,
            total_duration=total_duration
        )

        # 创建数据对比效果（使用我们改造后的函数）
        data_comparison_clip = self.create_data_comparison_effect(
            data=data,
            font_path='STXINWEI.TTF',
            font_size=28,
            start_time=data_start_time,
            total_duration=total_duration
        )

        # 定义图片最终位置和尺寸
        positions_and_sizes = {
            'main_avatar': {'position': (30, 100), 'size': (390, 255)},
            'compared_avatar': {'position': (480, 100), 'size': (390, 255)},
            'main_body': {'position': (5, 520), 'size': (440, 600)},
            'compared_body': {'position': (455, 520), 'size': (440, 600)}
        }

        main_avatar_anim = self.create_deal_animation(
            main_avatar_path,
            positions_and_sizes["main_avatar"]["position"],
            positions_and_sizes["main_avatar"]["size"],
            start_time=0.5,
            duration=0.2,
            total_duration=total_duration
        )

        compared_avatar_anim = self.create_deal_animation(
            compared_avatar_path,
            positions_and_sizes["compared_avatar"]["position"],
            positions_and_sizes["compared_avatar"]["size"],
            start_time=1,  # 稍微延迟，模拟发牌效果
            duration=0.2,
            total_duration=total_duration
        )

        main_body_anim = self.create_deal_animation(
            main_body_path,
            positions_and_sizes["main_body"]["position"],
            positions_and_sizes["main_body"]["size"],
            start_time=0.5,
            duration=0.3,
            total_duration=total_duration
        )

        compared_body_anim = self.create_deal_animation(
            compared_body_path,
            positions_and_sizes["compared_body"]["position"],
            positions_and_sizes["compared_body"]["size"],
            start_time=1,
            duration=0.3,
            total_duration=total_duration
        )

        # 创建黑色背景
        background = ColorClip(size=video_size, color=(0, 0, 0), duration=total_duration)

        def make_watermark_frame(t):
            img = PilImage.new("RGBA", (260, 80), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            # paste logo
            logo_img = PilImage.open("temp_logo.png").convert("RGBA")
            img.paste(logo_img, (10, 0), mask=logo_img)
            # paste text
            draw.text((100, 20), text='有一说一', font=title_font, fill='white')

            x0, y0, x1, y1 = 10, 0, 259, 79
            # 边框动画
            cycle = 10
            t_mod = t % cycle
            if t_mod < 2:  # 前2秒绘制边框
                progress = t_mod / 2
                draw = ImageDraw.Draw(img)

                # 上边
                draw.line([(x0, y0), (x0 + (x1 - x0) * progress, y0)], fill="white", width=3)
                # 右边
                draw.line([(x1, y0), (x1, y0 + (y1 - y0) * progress)], fill="white", width=3)
                # 下边
                draw.line([(x1, y1), (x1 - (x1 - x0) * progress, y1)], fill="white", width=3)
                # 左边
                draw.line([(x0, y1), (x0, y1 - (y1 - y0) * progress)], fill="white", width=3)
            elif t_mod < 5:
                draw.rectangle([x0, y0, x1, y1], outline="white", width=3)

            return np.array(img)

        watermark_clip = VideoClip(make_watermark_frame, duration=total_duration).with_position((20, video_size[1] - 150))

        # 将所有元素组合在一起
        final_video = CompositeVideoClip([
            background,
            main_avatar_anim,
            compared_avatar_anim,
            main_body_anim,
            compared_body_anim,
            static_bg_clip.with_position((0, 0)),  # 静态梯形背景
            typewriter_clip.with_position((0, 0)),  # 标题打字机文字
            name_typewriter_clip.with_position((0, 0)),  # 球员姓名打字机
            player_info_clip.with_position((0, 0)),  # 球员信息
            wipe_clip,
            data_comparison_clip.with_position((0, 0)),  # 数据对比
            watermark_clip
        ], size=video_size).with_duration(total_duration)

        # 设置总时长
        keyboard_audio = (AudioFileClip(keyboard_sound_path).with_volume_scaled(1.2)
                          .with_start(0.5))

        # 背景音乐：全程，匹配总时长
        bg_music = (AudioFileClip(bg_music_path).with_volume_scaled(0.2)
                    .with_duration(total_duration))
        # 合并音轨
        final_audio = CompositeAudioClip([keyboard_audio, bg_music])
        final_video = final_video.with_audio(final_audio)

        # 输出
        final_video.write_videofile(output_path, fps=24, audio_codec="aac")

    # 图片预处理函数
    def resize_images_for_vertical(self, main_avatar_path, compared_avatar_path, main_body_path, compared_body_path, logo_path):
        """调整图片尺寸以适应竖版视频"""

        # 调整main_avatar尺寸
        img = PilImage.open(main_avatar_path).convert("RGBA")
        img_resized = img.resize((390, 255), PilImage.LANCZOS)
        temp_path1 = "temp_main_avatar.png"
        img_resized.save(temp_path1, "PNG")
        self.temp_files.append(temp_path1)

        # 调整compared_avatar尺寸
        img = PilImage.open(compared_avatar_path).convert("RGBA")
        img_resized = img.resize((390, 255), PilImage.LANCZOS)
        temp_path2 = "temp_compared_avatar.png"
        img_resized.save(temp_path2, "PNG")
        self.temp_files.append(temp_path2)

        # 调整main_body尺寸
        img = PilImage.open(main_body_path).convert("RGBA")
        img_resized = img.resize((440, 700), PilImage.LANCZOS)
        temp_path3 = "temp_main_body.png"
        img_resized.save(temp_path3, "PNG")
        self.temp_files.append(temp_path3)

        # 调整compared_body尺寸
        img = PilImage.open(compared_body_path).convert("RGBA")
        img_resized = img.resize((440, 700), PilImage.LANCZOS)
        temp_path4 = "temp_compared_body.png"
        img_resized.save(temp_path4, "PNG")
        self.temp_files.append(temp_path4)

        img = PilImage.open(logo_path).convert("RGBA")
        img_resized = img.resize((80, 80), PilImage.LANCZOS)
        temp_path5 = "temp_logo.png"
        img_resized.save(temp_path5, "PNG")
        self.temp_files.append(temp_path5)

        return self.temp_files

    def generate_cover(self):
        pass
