import math

from typing import List


class TextUtils:
    def __init__(self, max_length: int = 20):
        """
        初始化文本分割器

        参数:
            max_length: 每段文本的最大长度(中文字符算1，数字和字母算0.5)
            punctuation_weights: 标点符号分割权重(优先级)
            hard_split: 是否允许强制分割(当找不到合适标点时)
        """
        self.max_length = max_length

        # 默认标点权重(数值越大优先级越高)
        self.punctuation_weights = {
            '。': 4, '！': 4, '？': 4,  # 句子结束
            '；': 3, '，': 2, '、': 2,  # 句子中间
            ' ': 1, '\n': 1,  # 空格和换行
            ',': 2, '.': 2, '!': 2, '?': 2  # 英文标点
        }

    def calculate_length(self, text: str) -> float:
        """计算文本有效长度(中文1，数字字母0.5)"""
        return sum(0.5 if char.isdigit() or char.isalpha() else 1
                   for char in text)

    def find_best_split_pos(self, text: str, start: int, end: int) -> int:
        """在指定范围内寻找最佳分割位置"""
        best_pos = -1
        best_weight = 0

        # 查找范围内的所有标点
        for i in range(start, min(end, len(text))):
            char = text[i]
            if char in self.punctuation_weights:
                weight = self.punctuation_weights[char]
                if weight > best_weight:
                    best_weight = weight
                    best_pos = i

        return best_pos

    def split_text(self, text: str) -> List[str]:
        """分割文本为多段"""
        segments = []
        remaining_text = text.strip()

        while remaining_text:
            # 如果剩余文本已经足够短
            if self.calculate_length(remaining_text) <= self.max_length:
                segments.append(remaining_text)
                break

            # 查找最佳分割点(在1.5倍max_length范围内)
            search_end = min(len(remaining_text), int(self.max_length * 1.5))
            split_pos = self.find_best_split_pos(remaining_text,
                                                 int(self.max_length * 0.8),
                                                 search_end)

            # 如果找到合适的分割点
            if split_pos > 0:
                segments.append(remaining_text[:split_pos + 1])
                remaining_text = remaining_text[split_pos + 1:].lstrip()
            else:
                # 无法分割又不允许强制分割，则整段保留
                segments.append(remaining_text)
                break

        return segments

    @staticmethod
    def split_title(text, ratio=(3, 2)):
        total_length = len(text)
        cut_length = int(total_length * (ratio[0] / float(sum(ratio))))

        # 按照字符切割文本
        part1 = text[:cut_length]
        part2 = text[cut_length:]

        return part1, part2
