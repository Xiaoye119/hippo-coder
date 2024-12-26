import os
import random
from difflib import SequenceMatcher
from collections import Counter
import re
import math
from statistics import stdev

testtesttesttest

# 定义关键词列表（可以根据实际需求调整）
KEYWORDS = [
    'module', 'endmodule', 'input', 'output', 'inout', 'wire', 'reg', 'integer',
    'parameter', 'localparam', 'function', 'endfunction', 'task', 'endtask',
    'if', 'else', 'case', 'casex', 'casez', 'default', 'for', 'while', 'repeat',
    'always', 'initial', 'begin', 'end', 'fork', 'join', 'posedge', 'negedge',
    'bit', 'logic', 'byte', 'shortint', 'int', 'longint', 'shortreal', 'chandle',
    'string', 'enum', 'struct', 'union', 'typedef', 'signed', 'unsigned',
    'interface', 'endinterface', 'modport', 'class', 'endclass', 'extends',
    'implements', 'virtual', 'import', 'export', 'package',
    'assert', 'assume', 'cover', 'expect', 'property', 'sequence',
    'rand', 'randc', 'constraint', 'with', 'inside'
]


def read_verilog_files(directory):
    """读取目录下的所有 Verilog 文件内容."""
    files_content = {}
    for filename in os.listdir(directory):
        if filename.endswith('.v'):
            filepath = os.path.join(directory, filename)
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as file:
                files_content[filename] = file.readlines()
    return files_content


def calculate_similarity_ratio(str1, str2):
    """计算两段字符串的相似度比率."""
    return SequenceMatcher(None, str1, str2).ratio()


def score_by_repetition(files_content, n=10):
    # TODO 整个文件的代码行数决定随机行数，设定个比例
    # TODO 分组，设置块大小，随机抽取块比对
    # TODO 分组，设按照上面的分组，计算交叉数，交叉数多的给更高的
    # TODO 迷你哈希计算相似度，minihash，行和行相比
    """根据重复程度打分."""
    scores = {}
    for filename, lines in files_content.items():
        sampled_lines = random.sample(lines, min(n, len(lines)))
        similarity_scores = []
        for i in range(len(sampled_lines)):
            for j in range(i + 1, len(sampled_lines)):
                ratio = calculate_similarity_ratio(sampled_lines[i], sampled_lines[j])
                similarity_scores.append(ratio)

        avg_similarity = sum(similarity_scores) / (len(similarity_scores) or 1)
        # 将相似度转换为分数，这里我们假设完全不相似得100分，完全相同得0分
        score = max(0, 100 - avg_similarity * 100)
        scores[filename] = score
    return scores


def score_by_keyword_occurrence(files_content):
    """根据关键词出现率打分."""
    # TODO 去掉注释，去掉标点
    scores = {}
    keyword_pattern = re.compile('|'.join(re.escape(kw) for kw in KEYWORDS))

    for filename, lines in files_content.items():
        content = ''.join(lines).lower()
        words = re.findall(r'\b\w+\b', content)
        matches = keyword_pattern.findall(content)
        total_keywords = len(matches)
        total_words = len(words)

        if total_words == 0:
            score = 0
        else:
            ratio_diff = total_keywords / total_words
            score = max((1 - ratio_diff) * 100)

        scores[filename] = int(score)
    return scores


def score_by_code_to_comment_ratio(files_content):
    """根据代码和注释的比例打分."""
    # TODO 考虑具体的任务：1主代码生成；2主注释代码转换
    scores = {}
    for filename, lines in files_content.items():
        code_lines = 0
        comment_lines = 0
        for line in lines:
            stripped_line = line.strip()
            if not stripped_line:
                continue
            if stripped_line.startswith('//') or stripped_line.startswith('/*') or stripped_line.endswith('*/'):
                comment_lines += 1
            else:
                code_lines += 1

        total_lines = code_lines + comment_lines
        if total_lines == 0:
            score = 0
        else:
            # 有效代码率越高得分越高
            score = (code_lines / total_lines) * 100
        scores[filename] = score
    return scores


def score_by_code_length_diversity(files_content, min_ideal_length=5, max_ideal_length=80, ideal_avg_length=40):
    """根据代码长度分布情况打分."""
    # TODO 测试每个代码计算的正确与否
    # TODO 单元测试
    scores = {}
    for filename, lines in files_content.items():
        lengths = [len(line.strip()) for line in lines if line.strip()]
        if not lengths:
            score = 0
        else:
            avg_length = sum(lengths) / len(lengths)
            length_stddev = stdev(lengths) if len(lengths) > 1 else 0
            within_range_ratio = sum(min_ideal_length <= length <= max_ideal_length for length in lengths) / len(
                lengths)

            # 考虑平均长度与理想长度的差距
            avg_length_diff = abs(avg_length - ideal_avg_length) / ideal_avg_length if ideal_avg_length != 0 else 0
            diversity_score = (1 - avg_length_diff) * 50  # 平均长度越接近理想值，得分越高

            # 标准差越大，表示长度越多样化，但不能无限大
            stddev_score = min(50, length_stddev * 10)

            # 综合考虑标准差和长度范围内的比例给出得分
            score = (diversity_score + stddev_score) * within_range_ratio
            score = min(100, max(0, score))

        scores[filename] = score
    return scores


def score_by_information_entropy(files_content):
    """根据单行信息熵打分，简化版."""

    def calculate_entropy(elements):
        if not elements:
            return 0
        counter = Counter(elements)
        probabilities = [count / len(elements) for count in counter.values()]
        return -sum(p * math.log2(p) for p in probabilities)

    scores = {}
    for filename, lines in files_content.items():
        entropies = [
            (calculate_entropy(line.replace(" ", "")), calculate_entropy(line.split()))
            for line in lines if line.strip()
        ]

        if not entropies:
            score = 0
        else:
            avg_char_entropy = sum(char_entropy for char_entropy, _ in entropies) / len(entropies)
            avg_word_entropy = sum(word_entropy for _, word_entropy in entropies) / len(entropies)
            score = (avg_char_entropy + avg_word_entropy) / 2
            score = min(100, score * 20)  # 最大得分为100

        scores[filename] = score
    return scores


def main():
    directory = r'./'

    files_content = read_verilog_files(directory)

    repetition_scores = score_by_repetition(files_content)
    keyword_scores = score_by_keyword_occurrence(files_content)
    code_comment_ratio_scores = score_by_code_to_comment_ratio(files_content)
    code_length_diversity_scores = score_by_code_length_diversity(files_content)
    information_entropy_scores = score_by_information_entropy(files_content)

    print("重复程度评分：")
    for filename, score in repetition_scores.items():
        print(f"文件名: {filename}, 评分: {score:.2f}")

    print("\n关键词出现率评分：")
    for filename, score in keyword_scores.items():
        print(f"文件名: {filename}, 评分: {score:.2f}")

    print("\n有效代码率评分：")
    for filename, score in code_comment_ratio_scores.items():
        print(f"文件名: {filename}, 评分: {score:.2f}")

    print("\n代码长度分布评分：")
    for filename, score in code_length_diversity_scores.items():
        print(f"文件名: {filename}, 评分: {score:.2f}")

    print("\n单行信息熵评分：")
    for filename, score in information_entropy_scores.items():
        print(f"文件名: {filename}, 评分: {score:.2f}")


if __name__ == "__main__":
    main()
