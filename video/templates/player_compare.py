import logging
import os
import re
import shutil
import traceback
import uuid

import numpy as np
from PIL import Image as PilImage, ImageDraw, ImageFont
from moviepy import *
from pydub import AudioSegment

from astra.settings import VIDEO_PATH, LOGO_PATH, IMG_PATH, TMP_PATH
from image.models import Image
from video.models import Video
from video.templates.video_template import VideoTemplate, VideoOrientation
from voice.models import Sound

logger = logging.getLogger("video")

title_font = ImageFont.truetype('STXINWEI.TTF', 40)
name_font = ImageFont.truetype('STXINWEI.TTF', 36)
data_font = ImageFont.truetype('STXINWEI.TTF', 30)
background_color = '#ffffff'


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
        self.tmps = None

    def process(self, user, video_id, parameters):
        """实现带字幕和音频同步的视频生成

        Args:
            video_id: 视频唯一ID
            parameters: 包含图片路径列表和文本的参数
            :param user: 创建者
        """
        self.tmps = os.path.join(TMP_PATH, video_id)
        if not os.path.exists(self.tmps):
            os.mkdir(self.tmps)
        logger.info(f"视频生成请求参数：{parameters}")
        project_name = parameters.get('title')
        param_id = self.save_parameters(self.template_id, user, project_name, parameters)

        # 获取开场部分和视频主体内容
        start_text = parameters.get('start_text', '').replace('·', '')

        bgm = parameters.get('bgm')  # 获取背景音乐路径
        content = parameters.get('content')
        main_data = parameters.get('main', {})
        compared_data = parameters.get('compared', {})
        main_avatar_path = main_data['avatar']
        compared_avatar_path = compared_data['avatar']
        main_body_path = main_data['body']
        compared_body_path = compared_data['body']

        resized_main_avatar_path = os.path.join(self.tmps, 'resized_main_avatar.png')
        avatar_img = PilImage.open(main_avatar_path)
        resized_img = self.img_utils.resize_and_crop(avatar_img, 390, 255)
        resized_img.save(resized_main_avatar_path)

        resized_compared_avatar_path = os.path.join(self.tmps, 'resized_compared_avatar.png')
        avatar_img = PilImage.open(compared_avatar_path)
        resized_img = self.img_utils.resize_and_crop(avatar_img, 390, 255)
        resized_img.save(resized_compared_avatar_path)

        trim_main_body_path = os.path.join(self.tmps, 'trim_main_body.png')
        self.img_utils.trim_image(main_body_path, trim_main_body_path)
        trim_compared_body_path = os.path.join(self.tmps, 'trim_compared_body.png')
        self.img_utils.trim_image(compared_body_path, trim_compared_body_path)

        output_path = os.path.join(VIDEO_PATH, f"{video_id}.mp4")

        reader = parameters.get('reader')
        self.default_speaker = reader

        Video(creator=user, title=f"{main_data.get('name').split('·')[-1]}vs{compared_data.get('name').split('·')[-1]}{project_name}", content=content, video_type=self.video_type,
              result='Process',
              process=0.0, id=video_id, param_id=param_id).save()
        try:
            cover_id = self.generate_cover(project_name, main_data, compared_data, user)
            Video.objects.filter(id=video_id).update(cover=cover_id)
            segments = self.text_utils.split_text(start_text)

            subtitlers = []
            start = 0.5
            final_audio = AudioSegment.silent(duration=0)

            for i, sg in enumerate(segments):
                sg.replace("VS", '<break time="100ms"/>VS<break time="100ms"/>')
                tts = self.speech.chat_tts_sync(sg, reader, user, video_id)
                tts_path = os.path.join(self.tts_path, f'{tts.id}.{tts.format}')
                audio = AudioSegment.from_file(tts_path).fade_in(200).fade_out(200)
                for text_clip in self.subtitler.text_clip(sg, start, tts.duration, 1310, self.width):
                    subtitlers.append(text_clip)
                if i == 0:
                    final_audio = audio
                    start += tts.duration
                else:
                    final_audio = final_audio.append(audio, crossfade=200)
                    start += tts.duration - 0.2
            audio_path = os.path.join(self.tmps, "merged_tts.mp3")
            final_audio.export(audio_path, format="mp3")

            Video.objects.filter(id=video_id).update(process=0.2)

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
                                           resized_main_avatar_path, resized_compared_avatar_path,
                                           trim_main_body_path, trim_compared_body_path,
                                           output_path, data,
                                           audio_path,  # 开场音频文件
                                           subtitlers,
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
            if os.path.exists(self.tmps):
                shutil.rmtree(self.tmps)

    def create_deal_animation(self, img_path, final_position, start_time, duration, total_duration):
        """
        创建类似“发牌”的动画：图片从右上角快速飞到指定位置
        """
        # 使用PIL加载并调整图片尺寸
        pil_img = PilImage.open(img_path).convert("RGBA")

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

    def create_name_typewriter_effect(self, data, start_time, total_duration):
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

                # 计算当前应该显示的文字长度
                progress = min(1, (t - start_time) / 1)  # 名字打字效果持续1秒（你可以调整）

                # 主球员名字打字效果
                main_name = main.get('name')
                main_chars_to_show = int(len(main_name) * progress)
                current_main_text = main_name[:main_chars_to_show]
                main_mask = name_font.getmask(current_main_text)
                draw.text((225 - int(main_mask.size[0]) / 2, 315), text=current_main_text, font=name_font, fill='red')

                # 对比球员名字打字效果
                compared_name = compared.get('name')
                compared_chars_to_show = int(len(compared_name) * progress)
                current_compared_text = compared_name[:compared_chars_to_show]
                compared_mask = name_font.getmask(current_compared_text)
                draw.text((675 - int(compared_mask.size[0]) / 2, 315), text=current_compared_text, font=name_font, fill='yellow')

            return np.array(img)

        return VideoClip(make_frame, duration=total_duration)

    # 创建打字机效果，并在完成后保持显示
    def create_typewriter_effect(self, text, position, duration, total_duration, bg_points=None):
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
                draw.polygon(bg_points, fill="#66666")

            # 计算当前应该显示的文字长度
            if t < duration:
                progress = min(1, t / duration)
                chars_to_show = int(len(text) * progress)
                current_text = text[:chars_to_show]
            else:
                current_text = text  # 动画完成后显示完整文字

            # 绘制文字

            draw.text(position, current_text, font=title_font, fill="gold")

            return np.array(img)

        return VideoClip(make_frame, duration=total_duration)

    # 创建静态梯形背景
    def create_static_background(self, bg_points, total_duration, title_y, hex_height):
        """
        创建静态梯形背景
        """

        def make_frame(t):
            img = PilImage.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.line([(30, title_y + hex_height / 2), (870, title_y + hex_height / 2)], fill=background_color, width=2)
            draw.polygon(bg_points, fill="#333333")
            return np.array(img)

        return VideoClip(make_frame, duration=total_duration)

    # 创建球员信息显示效果（在所有图片到达后显示）
    def create_player_info_effect(self, data, start_time, total_duration):
        """
        创建球员信息显示效果
        """

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
                draw.text((225 - int(data_font.getmask(main_draft).size[0]) / 2, 370), text=main_draft, font=data_font, fill=background_color)
                draw.text((675 - int(data_font.getmask(compared_draft).size[0]) / 2, 370), text=compared_draft, font=data_font, fill=background_color)

                # 绘制比赛结果
                main_game_result = main.get('game_result')
                compared_game_result = compared.get('game_result')
                draw.text((225 - int(name_font.getmask(main_game_result).size[0]) / 2, 415), text=main_game_result, font=name_font,
                          fill='red')
                draw.text((675 - int(name_font.getmask(compared_game_result).size[0]) / 2, 415), text=compared_game_result, font=name_font,
                          fill='yellow')

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

    def create_data_comparison_effect(self, data, start_time, total_duration):
        """
        创建数据对比效果：
        - 左边的数据槽从右往左填充
        - 右边的数据槽从左往右填充
        - 类型文字在动画过程中为红色，结束后为白色
        - 数据数值从0逐渐增加到最终值
        - 进度条由浅到深渐变，结束时更好的一方为红色
        - 更好的一方数值最终显示为红色
        """

        background_color = '#ffffff'

        # 基础颜色
        left_base_light = (128, 0, 0, 192)  # 浅红
        left_base_dark = (255, 0, 0, 192)  # 深红（最终色）

        right_base_light = (255, 255, 128, 192)  # 浅黄
        right_base_dark = (255, 255, 0, 192)  # 深黄（最终色）

        # 数据槽位置参数
        bar_y_start = 600
        bar_height = 40
        bar_spacing = 60
        left_bar_x1, left_bar_x2 = 60, 380
        right_bar_x1, right_bar_x2 = 520, 840

        left_total = left_bar_x2 - left_bar_x1
        right_total = right_bar_x2 - right_bar_x1

        main_data = data['main']['data']
        compared_data = data['compared']['data']
        data_items = list(main_data.keys())

        percent_items = ['投篮', '三分球', '罚球', '胜率']
        int_items = ['出战场次']

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
                    label_width = data_font.getmask(item).size[0]
                    label_x = 450 - label_width / 2
                    draw.text((label_x, bar_y + (bar_height - 24) // 2),
                              text=item, font=data_font, fill=label_color)

                    # 边框
                    draw.rectangle([left_bar_x1, bar_y, left_bar_x2, bar_y + bar_height], outline=background_color, width=1)
                    draw.rectangle([right_bar_x1, bar_y, right_bar_x2, bar_y + bar_height], outline=background_color, width=1)

                    main_value = main_data[item]
                    compared_value = compared_data[item]

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

                    draw.text((65,
                               bar_y + (bar_height - 20) // 2),
                              text=main_data_text, font=data_font, fill=background_color)

                    draw.text((right_bar_x2 - data_font.getmask(compared_data_text).size[0] - 5,
                               bar_y + (bar_height - 20) // 2),
                              text=compared_data_text, font=data_font, fill=background_color)

            return np.array(img)

        return VideoClip(make_frame, duration=total_duration)

    # 主函数
    def create_video_with_effects(self, title, main_avatar_path, compared_avatar_path, main_body_path, compared_body_path, output_path, data,
                                  audio_path, subtitlers, bg_music_path):
        # 竖版视频尺寸
        video_size = (self.width, self.height)
        audio_clip = AudioFileClip(audio_path).with_start(0.5)
        # 设置持续时间
        total_duration = audio_clip.duration + 1  # 总时长延长到30秒，因为数据对比需要时间
        animation_duration = 2  # 动画效果时长2秒
        info_start_time = 2  # 球员信息在第2.5秒开始显示
        data_start_time = 5.0  # 数据对比在第5秒开始显示

        title_mask = title_font.getmask(title)
        title_width = title_mask.size[0]
        title_height = title_mask.size[1]
        title_x = 450 - title_width / 2
        title_y = 470

        # 六边形宽度和高度
        hex_width = title_width + 100
        hex_height = title_height + 40

        # 计算六边型6个点的坐标
        hex_points = [
            (450 - hex_width / 2, title_y + hex_height / 2),  # 左上
            (450 - title_width / 2, title_y),  # 上左
            (450 + title_width / 2, title_y),  # 上右
            (450 + hex_width / 2, title_y + hex_height / 2),  # 右上
            (450 + title_width / 2, title_y + hex_height),  # 右下
            (450 - title_width / 2, title_y + hex_height)  # 左下
        ]

        # 创建静态梯形背景（全程显示）
        static_bg_clip = self.create_static_background(hex_points, total_duration, title_y, hex_height)

        # 创建打字机效果（和图片动画同时开始）
        typewriter_clip = self.create_typewriter_effect(
            text=title,
            position=(title_x, title_y + 20),
            duration=animation_duration,
            total_duration=total_duration,
            bg_points=None
        )

        # 创建球员信息显示效果
        player_info_clip = self.create_player_info_effect(
            data=data,
            start_time=info_start_time + 1,
            total_duration=total_duration
        )

        wipe_clip = self.create_wipe_effect(
            img_path=os.path.join(LOGO_PATH, 'vs.png'),
            pos=(369, 100),
            start_time=info_start_time + 1,
            duration=0.5,
            video_duration=total_duration  # 整个视频时长
        )

        # 创建球员姓名打字机效果
        name_typewriter_clip = self.create_name_typewriter_effect(
            data=data,
            start_time=info_start_time,
            total_duration=total_duration
        )

        # 创建数据对比效果（使用我们改造后的函数）
        data_comparison_clip = self.create_data_comparison_effect(
            data=data,
            start_time=data_start_time,
            total_duration=total_duration
        )

        main_body_pil_image = PilImage.open(main_body_path)
        main_body_width, main_body_height = main_body_pil_image.size

        compared_body_pil_image = PilImage.open(compared_body_path)
        compared_body_width, compared_body_height = compared_body_pil_image.size

        # 定义图片最终位置和尺寸
        positions_and_sizes = {
            'main_avatar': {'position': (30, 50)},
            'compared_avatar': {'position': (480, 50)},
            'main_body': {'position': (int((450 - main_body_width) / 2), 590 + int((700 - main_body_height) / 2))},
            'compared_body': {'position': (450 + int((450 - compared_body_width) / 2), 590 + int((700 - compared_body_height) / 2))}
        }

        main_avatar_anim = self.create_deal_animation(
            main_avatar_path,
            positions_and_sizes["main_avatar"]["position"],
            start_time=0.5,
            duration=0.2,
            total_duration=total_duration
        )

        compared_avatar_anim = self.create_deal_animation(
            compared_avatar_path,
            positions_and_sizes["compared_avatar"]["position"],
            start_time=1,  # 稍微延迟，模拟发牌效果
            duration=0.2,
            total_duration=total_duration
        )

        main_body_anim = self.create_deal_animation(
            main_body_path,
            positions_and_sizes["main_body"]["position"],
            start_time=0.5,
            duration=0.3,
            total_duration=total_duration
        )

        compared_body_anim = self.create_deal_animation(
            compared_body_path,
            positions_and_sizes["compared_body"]["position"],
            start_time=1,
            duration=0.3,
            total_duration=total_duration
        )

        # 创建黑色背景
        background = ColorClip(size=video_size, color=(0, 0, 0), duration=total_duration)

        def make_watermark_frame(t):
            img = PilImage.new("RGBA", (850, 80), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            # paste logo
            logo_img = PilImage.open(os.path.join(LOGO_PATH, 'logo.png')).resize((80, 80)).convert("RGBA")
            img.paste(logo_img, (470, 0), mask=logo_img)
            # paste text
            draw.text((540, 20), text='数据之眼', font=title_font, fill='white')

            x0, y0, x1, y1 = 460, 0, 709, 79
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

        watermark_clip = VideoClip(make_watermark_frame, duration=total_duration).with_position((50, video_size[1] - 200))

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
            watermark_clip,
            *subtitlers
        ], size=video_size).with_duration(total_duration)
        # 背景音乐：全程，匹配总时长
        bg_music = (AudioFileClip(bg_music_path).with_volume_scaled(0.1)
                    .with_duration(total_duration))
        # 合并音轨
        final_audio = CompositeAudioClip([audio_clip, bg_music])
        final_video = final_video.with_audio(final_audio)

        # 输出
        final_video.write_videofile(output_path, fps=24, audio_codec="aac")

    # 图片预处理函数

    def generate_cover(self, title, main_info, compared_info, user):
        new_img = PilImage.new('RGBA', (900, 1600), color=(0, 0, 0, 255))
        draw = ImageDraw.Draw(new_img)

        background_color = '#ffffff'
        tangle_color = '#666666'
        text_font = ImageFont.truetype('STXINWEI.TTF', 30)
        title_font = ImageFont.truetype('STXINWEI.TTF', 44)
        name_font = ImageFont.truetype('STXINWEI.TTF', 36)

        # 粘贴头像
        main_avatar_file = main_info['avatar']
        main_avatar = PilImage.open(main_avatar_file).convert("RGBA").resize((390, 255))

        compared_avatar_file = compared_info['avatar']
        compared_avatar = PilImage.open(compared_avatar_file).convert("RGBA").resize((390, 255))

        new_img.paste(main_avatar, (30, 50), main_avatar)
        new_img.paste(compared_avatar, (480, 50), compared_avatar)

        main_body_file = main_info['body']
        main_body = PilImage.open(main_body_file).convert("RGBA")

        compared_body_file = compared_info['body']
        compared_body = PilImage.open(compared_body_file).convert("RGBA")

        new_img.paste(main_body, (5, 580), main_body)
        new_img.paste(compared_body, (455, 580), compared_body)

        # 绘制球员姓名
        main_name = main_info.get('name')
        main_mask = name_font.getmask(main_name)
        compared_name = compared_info.get('name')
        compared_mask = name_font.getmask(compared_name)
        draw.text((225 - int(main_mask.size[0]) / 2, 315), text=main_name, font=name_font, fill='red')
        draw.text((675 - int(compared_mask.size[0]) / 2, 315), text=compared_name, font=name_font, fill='yellow')

        # 绘制选秀信息
        main_draft = main_info.get('draft')
        compared_draft = compared_info.get('draft')
        draw.text((225 - int(text_font.getmask(main_draft).size[0]) / 2, 370), text=main_draft, font=text_font, fill=background_color)
        draw.text((675 - int(text_font.getmask(compared_draft).size[0]) / 2, 370), text=compared_draft, font=text_font, fill=background_color)

        # 绘制比赛结果
        main_game_result = main_info.get('game_result')
        compared_game_result = compared_info.get('game_result')
        draw.text((225 - int(name_font.getmask(main_game_result).size[0]) / 2, 415), text=main_game_result, font=name_font, fill='red')
        draw.text((675 - int(name_font.getmask(compared_game_result).size[0]) / 2, 415), text=compared_game_result, font=name_font,
                  fill='yellow')

        # 先计算标题文本尺寸
        title_mask = title_font.getmask(title)
        title_width = title_mask.size[0]
        title_height = title_mask.size[1]
        title_x = 450 - title_width / 2
        title_y = 470

        # 计算六边形六个点的坐标
        # 六边形宽度和高度
        hex_width = title_width + 100
        hex_height = title_height + 40

        draw.line([(30, title_y + hex_height / 2), (870, title_y + hex_height / 2)], fill='#333333', width=2)
        # 计算梯形四个点的坐标（确保是真正的梯形）
        hex_points = [
            (450 - hex_width / 2, title_y + hex_height / 2),  # 左上
            (450 - title_width / 2, title_y),  # 上左
            (450 + title_width / 2, title_y),  # 上右
            (450 + hex_width / 2, title_y + hex_height / 2),  # 右上
            (450 + title_width / 2, title_y + hex_height),  # 右下
            (450 - title_width / 2, title_y + hex_height)  # 左下
        ]

        # 绘制梯形背景
        draw.polygon(hex_points, fill="gray")

        # 绘制标题（在背景之上）
        draw.text((title_x, title_y + 20), text=title, font=title_font, fill='gold')

        # 绘制数据标签和数据槽（在同一行）
        bar_y = 600  # 数据槽和标签的y坐标
        bar_height = 40
        # 数据槽位置
        left_bar_x1, left_bar_x2 = 60, 380  # 左边数据槽：50到380
        right_bar_x1, right_bar_x2 = 520, 840  # 右边数据槽：520到850

        dark_red = (255, 0, 0, 192)  # 深红色
        dark_yellow = (255, 192, 0, 192)  # 深蓝色

        main_data = main_info.get('data')
        compared_data = compared_info.get('data')
        data_font = ImageFont.truetype('STXINWEI.TTF', 20)

        # 定义百分比项目
        percent_items = ['投篮', '三分球', '罚球', '胜率']
        int_items = ['出战场次']

        def fmt_value(item, v):
            if item in percent_items:
                return f"{round(v, 1)}%" if isinstance(v, float) else f"{v}%"
            elif item in int_items:
                return f"{int(v)}"
            else:
                return f"{round(v, 1)}" if isinstance(v, float) else f"{v}"

        for item in main_data.keys():
            main_value = main_data.get(item)
            compared_value = compared_data.get(item)

            # 绘制数据槽边框
            draw.rectangle([left_bar_x1, bar_y, left_bar_x2, bar_y + bar_height],
                           outline=tangle_color, width=1, fill=None)
            draw.rectangle([right_bar_x1, bar_y, right_bar_x2, bar_y + bar_height],
                           outline=tangle_color, width=1, fill=None)

            # 计算进度条宽度
            left_total = left_bar_x2 - left_bar_x1
            right_total = right_bar_x2 - right_bar_x1

            if main_value == compared_value:
                # 数值相等，都填充红色
                left_width = left_total
                right_width = right_total

                # 绘制左侧进度条（从右向左）
                red_layer = PilImage.new('RGBA', (left_width, bar_height), dark_red)
                new_img.paste(red_layer, (left_bar_x2 - left_width, bar_y), red_layer)

                # 绘制右侧进度条（从左向右）
                red_layer = PilImage.new('RGBA', (right_width, bar_height), dark_yellow)
                new_img.paste(red_layer, (right_bar_x1, bar_y), red_layer)

            else:
                # 常规项，值越大越好
                if main_value > compared_value:
                    # 左侧（主球员）表现更好，填充红色
                    left_width = left_total
                    # 右侧（对比球员）按比例填充蓝色
                    right_width = int(right_total * (compared_value / main_value)) if main_value != 0 else 0

                    # 绘制左侧进度条（从右向左）
                    red_layer = PilImage.new('RGBA', (left_width, bar_height), dark_red)
                    new_img.paste(red_layer, (left_bar_x2 - left_width, bar_y), red_layer)

                    # 绘制右侧进度条（从左向右）
                    yellow_layer = PilImage.new('RGBA', (right_width, bar_height), dark_yellow)
                    new_img.paste(yellow_layer, (right_bar_x1, bar_y), yellow_layer)



                else:
                    # 右侧（对比球员）表现更好，填充红色
                    right_width = right_total
                    # 左侧（主球员）按比例填充蓝色
                    left_width = int(left_total * (main_value / compared_value)) if compared_value != 0 else 0

                    # 绘制左侧进度条（从右向左）
                    yellow_layer = PilImage.new('RGBA', (left_width, bar_height), dark_red)
                    new_img.paste(yellow_layer, (left_bar_x2 - left_width, bar_y), yellow_layer)

                    # 绘制右侧进度条（从左向右）
                    red_layer = PilImage.new('RGBA', (right_width, bar_height), dark_yellow)
                    new_img.paste(red_layer, (right_bar_x1, bar_y), red_layer)

            # 绘制数据标签
            label_width = text_font.getmask(item).size[0]
            label_x = 450 - label_width / 2  # 居中
            draw.text((label_x, bar_y + (bar_height - 24) // 2), text=item, font=text_font, fill=background_color)

            # 显示具体数据
            main_data_text = fmt_value(item, main_value)
            compared_data_text = fmt_value(item, compared_value)

            draw.text((65, bar_y + (bar_height - 20) // 2),
                      text=main_data_text, font=data_font, fill=background_color)

            draw.text((right_bar_x2 - data_font.getmask(compared_data_text).size[0] - 5, bar_y + (bar_height - 20) // 2),
                      text=compared_data_text, font=data_font, fill=background_color)

            bar_y += 60

        image_id = uuid.uuid4()
        image_name = f'{image_id}.png'

        logo_img = PilImage.open(os.path.join(LOGO_PATH, 'logo.png')).convert("RGBA")

        logo_image = logo_img.resize((80, 80))
        new_img.paste(logo_image, (20, 1600 - 165), logo_image)

        draw.text((90, 1600 - 140), text="数据之眼", font=text_font, fill=background_color)
        new_img.save(os.path.join(IMG_PATH, image_name))

        spec = {
            'format': 'png',
            'mode': 'RGBA'
        }

        Image(
            id=image_id,
            img_name=image_name,
            category='normal',
            img_path=IMG_PATH,
            width=900,
            height=1600,
            creator=user,
            spec=spec
        ).save()

        return image_id
