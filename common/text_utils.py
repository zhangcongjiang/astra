import logging
import os
import re
import subprocess
import tempfile
from typing import List
from django.conf import settings

logger = logging.getLogger("text")


class TextUtils:
    def __init__(self, max_length: int = 20):
        self.max_length = max_length
        self.punctuation_weights = {
            '。': 4, '！': 4, '？': 4,  # 句子结束
            '；': 3, '，': 2, '、': 2,  # 句子中间
            ' ': 1, '\n': 1,  # 空格和换行
            ',': 2, '!': 2, '?': 2  # 英文标点
        }

    def calculate_length(self, text: str) -> float:
        return sum(0.5 if char.isdigit() or char.isalpha() else 1
                   for char in text)

    def find_best_split_pos(self, text: str, start: int, end: int) -> int:
        best_pos = -1
        best_weight = 0
        for i in range(start, min(end, len(text))):
            char = text[i]
            if char in self.punctuation_weights:
                weight = self.punctuation_weights[char]
                if weight > best_weight:
                    best_weight = weight
                    best_pos = i
        return best_pos

    def split_text_by_length(self, text: str) -> List[str]:
        """对一段文本按长度切分"""
        segments = []
        remaining_text = text.strip()
        while remaining_text:
            if self.calculate_length(remaining_text) <= self.max_length:
                segments.append(remaining_text)
                break

            search_end = min(len(remaining_text), int(self.max_length * 1.5))
            split_pos = self.find_best_split_pos(remaining_text,
                                                 int(self.max_length * 0.8),
                                                 search_end)
            if split_pos > 0:
                segments.append(remaining_text[:split_pos + 1])
                remaining_text = remaining_text[split_pos + 1:].lstrip()
            else:
                segments.append(remaining_text)
                break
        return segments

    def split_text(self, text: str) -> List[str]:
        """先按标点符号切分，再按长度切分，返回段落不带标点"""
        # 构造正则匹配所有标点
        punctuation_chars = ''.join(self.punctuation_weights.keys())

        # 按标点分割，同时保留标点
        initial_segments = re.split(f'([{re.escape(punctuation_chars)}])', text)

        combined_segments = []
        for i in range(0, len(initial_segments) - 1, 2):
            segment = (initial_segments[i] + initial_segments[i + 1]).strip()
            if segment:
                # 去掉段尾标点
                if segment[-1] in punctuation_chars:
                    segment = segment[:-1]
                combined_segments.append(segment)

        # 处理末尾没有标点的部分
        if len(initial_segments) % 2 != 0 and initial_segments[-1].strip():
            combined_segments.append(initial_segments[-1].strip())

        # 对每段再按长度切分
        final_segments = []
        for seg in combined_segments:
            final_segments.extend(self.split_text_by_length(seg))

        return final_segments

    def _preprocess_markdown_images(self, md_content: str) -> str:
        """
        预处理markdown内容中的图片路径，将相对路径转换为绝对路径
        """
        # 匹配markdown图片语法: ![alt text](/media/images/filename.ext)
        image_pattern = r'!\[([^\]]*)\]\((/media/[^)]+)\)'
        
        def replace_image_path(match):
            alt_text = match.group(1)
            relative_path = match.group(2)
            
            # 移除开头的斜杠，构建完整的文件路径
            if relative_path.startswith('/media/'):
                file_path = relative_path[1:]  # 移除开头的斜杠
                absolute_path = os.path.join(settings.BASE_DIR, file_path)
                
                # 检查文件是否存在
                if os.path.exists(absolute_path):
                    # 使用绝对路径替换相对路径
                    return f'![{alt_text}]({absolute_path})'
                else:
                    logger.warning(f"图片文件不存在: {absolute_path}")
                    # 如果文件不存在，保持原样
                    return match.group(0)
            
            return match.group(0)
        
        # 替换所有匹配的图片路径
        processed_content = re.sub(image_pattern, replace_image_path, md_content)
        return processed_content

    def convert_md_to_doc(self, md_file, doc_file):
        # 检查文件是否存在
        if not os.path.exists(md_file):
            logger.info(f"Markdown 文件 '{md_file}' 不存在.")
            return

        try:
            # 读取原始markdown文件内容
            with open(md_file, 'r', encoding='utf-8') as f:
                md_content = f.read()
            
            # 预处理图片路径
            processed_content = self._preprocess_markdown_images(md_content)
            
            # 创建临时文件保存处理后的内容
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as temp_file:
                temp_file.write(processed_content)
                temp_md_file = temp_file.name
            
            try:
                # 调用 Pandoc 进行转换，使用处理后的临时文件
                subprocess.run(["pandoc", temp_md_file, "-o", doc_file, "--preserve-tabs"], check=True)
                logger.info(f"成功将 '{md_file}' 转换为 '{doc_file}'，已处理图片路径.")
            finally:
                # 清理临时文件
                if os.path.exists(temp_md_file):
                    os.unlink(temp_md_file)
                    
        except subprocess.CalledProcessError as e:
            logger.error(f"转换失败: {e}")
        except Exception as e:
            logger.error(f"处理markdown文件时发生错误: {e}")
