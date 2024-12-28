import os
import subprocess
import re
import random
from tqdm import tqdm
import pandas as pd
from difflib import SequenceMatcher
from collections import Counter
import math
from statistics import stdev
import chardet

# 定义关键词列表
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

# 检查 iverilog 是否安装
def check_iverilog_installed():
    try:
        subprocess.run(["iverilog", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except FileNotFoundError:
        print("Error: iverilog 未安装或未配置在 PATH 中。\n请参考官方文档进行安装：https://iverilog.fandom.com/wiki/Installation")
        return False

# 自动检测文件编码
def detect_encoding(file_path):
    with open(file_path, 'rb') as f:
        raw = f.read()
        result = chardet.detect(raw)
        return result['encoding']

# 查找 Verilog 文件
def find_verilog_files(directory, recursive=False):
    verilog_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".v"):
                verilog_files.append(os.path.join(root, file))
        if not recursive:
            break
    return verilog_files[:50]

# 检查 Verilog 语法
def check_verilog_syntax(file_path, include_paths=None):
    """
    检查 Verilog 文件的语法错误，并计算错误行数占比。

    Args:
        file_path (str): Verilog 文件路径。
        include_paths (list, optional): 包含路径列表。

    Returns:
        dict: 包含是否成功、错误行数、总行数、错误比例的信息。
    """
    try:
        cmd = ["iverilog", "-t", "null"]
        if include_paths:
            for path in include_paths:
                cmd.extend(["-I", path])
        cmd.append(file_path)

        process = subprocess.run(
            cmd,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        # 如果没有异常被抛出，说明编译成功
        encoding = detect_encoding(file_path) or 'utf-8'
        with open(file_path, "r", encoding=encoding) as file:
            total_lines = sum(1 for _ in file)

        return {
            "file": file_path,
            "success": True,
            "total_lines": total_lines,
            "error_lines": 0,
            "error_ratio": 0,
            "errors": ""
        }
    except subprocess.CalledProcessError as e:
        error_lines = set()
        for line in e.stderr.splitlines():
            match = re.search(r"(\d+): error:", line)
            if match:
                error_lines.add(int(match.group(1)))

        encoding = detect_encoding(file_path) or 'utf-8'
        with open(file_path, "r", encoding=encoding) as file:
            total_lines = sum(1 for _ in file)

        error_count = len(error_lines)
        error_ratio = error_count / total_lines if total_lines > 0 else 0

        return {
            "file": file_path,
            "success": False,
            "total_lines": total_lines,
            "error_lines": error_count,
            "error_ratio": error_ratio,
            "errors": e.stderr.strip()  # 添加错误信息
        }
    except Exception as e:
        return {
            "file": file_path,
            "success": False,
            "total_lines": 0,
            "error_lines": 0,
            "error_ratio": 0,
            "errors": str(e)
        }

# 评分函数定义
def calculate_similarity_ratio(str1, str2):
    return SequenceMatcher(None, str1, str2).ratio()

def score_by_repetition(files_content, sample_rate=0.3):
    scores = {}
    for filename, lines in files_content.items():
        curr_lines_num = len(lines)
        sample_lines_num = int(curr_lines_num * sample_rate)
        sampled_lines = random.sample(lines, max(1, sample_lines_num))

        similarity_scores = []
        for i in range(len(sampled_lines)):
            for j in range(i + 1, len(sampled_lines)):
                ratio = calculate_similarity_ratio(sampled_lines[i], sampled_lines[j])
                similarity_scores.append(ratio)

        avg_similarity = sum(similarity_scores) / (len(similarity_scores) or 1)
        score = max(0, 100 - avg_similarity * 100)
        scores[filename] = round(score, 2)  # 保留两位小数
    return scores

def score_by_keyword_occurrence(files_content):
    """根据关键词出现率打分."""
    scores = {}
    keyword_pattern = re.compile('|'.join(re.escape(kw) for kw in KEYWORDS))

    for filename, lines in files_content.items():
        cleaned_lines = []  # 去掉注释和标点后的行数据
        continue_content = [' ', "\n\n", "\t", "\n"]
        for line in lines:
            if line in continue_content:
                continue
            line = re.sub(r'//.*|/\*.*?\*/', '', line)  # 去掉单行和多行注释
            line = re.sub(r'[\W_]+', ' ', line)  # 去掉标点
            cleaned_lines.append(line)
        content = ' '.join(cleaned_lines).lower()
        words = re.findall(r'\b\w+\b', content)
        matches = keyword_pattern.findall(content)
        total_keywords = len(matches)
        unique_keywords = len(set(matches))
        total_words = len(words)

        if total_words == 0 or total_keywords == 0:
            score = 0.0
        else:
            ratio_diff = total_keywords / total_words
            no_repeat = unique_keywords / total_keywords
            combined_ratio = 0.8 * (1 - ratio_diff) + 0.2 * no_repeat
            score = max(combined_ratio * 100, 0)

        scores[filename] = round(score, 2)  # 保留两位小数
    return scores

def score_by_code_to_comment_ratio(files_content):
    """根据代码和注释的比例打分."""
    scores = {}
    for filename, lines in files_content.items():
        code_lines = 0
        comment_lines = 0
        block_comment = False

        for line in lines:
            stripped_line = line.strip()
            if not stripped_line:
                continue

            if block_comment:
                comment_lines += 1
                if '*/' in stripped_line:
                    block_comment = False
                    stripped_line = stripped_line.split('*/', 1)[1].strip()
                else:
                    continue

            if '/*' in stripped_line:
                before_comment, after_comment = stripped_line.split('/*', 1)
                if before_comment.strip():
                    code_lines += 1
                comment_lines += 1
                block_comment = True
                stripped_line = after_comment.split('*/', 1)[-1].strip() if '*/' in after_comment else ''
                if not stripped_line:
                    continue

            if '//' in stripped_line:
                before_comment, _ = stripped_line.split('//', 1)
                if before_comment.strip():
                    code_lines += 1
                comment_lines += 1
                continue

            if stripped_line:
                code_lines += 1

        total_lines = code_lines + comment_lines
        if total_lines == 0:
            score = 0.0
        else:
            score = (code_lines / total_lines) * 100

        scores[filename] = round(score, 2)  # 保留两位小数
    return scores

def score_by_code_length_diversity(files_content, min_ideal_length=5, max_ideal_length=80, ideal_avg_length=40):
    scores = {}
    for filename, lines in files_content.items():
        lengths = [len(line.strip()) for line in lines if line.strip()]
        if not lengths:
            scores[filename] = 0.00
            continue

        avg_length = sum(lengths) / len(lengths)
        length_stddev = stdev(lengths) if len(lengths) > 1 else 0
        within_range_ratio = sum(min_ideal_length <= length <= max_ideal_length for length in lengths) / len(lengths)

        avg_length_diff = abs(avg_length - ideal_avg_length) / ideal_avg_length if ideal_avg_length != 0 else 0
        diversity_score = (1 - avg_length_diff) * 50
        stddev_score = min(50, length_stddev * 10)
        score = (diversity_score + stddev_score) * within_range_ratio
        scores[filename] = round(min(100, max(0, score)), 2)  # 保留两位小数
    return scores

def score_by_information_entropy(files_content):
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
            scores[filename] = 0.00
            continue

        avg_char_entropy = sum(char_entropy for char_entropy, _ in entropies) / len(entropies)
        avg_word_entropy = sum(word_entropy for _, word_entropy in entropies) / len(entropies)
        score = (avg_char_entropy + avg_word_entropy) / 2 * 20
        scores[filename] = round(min(100, score), 2)  # 保留两位小数
    return scores

# 主函数
def main():
    if not check_iverilog_installed():
        exit(1)

    target_directory = os.getcwd()
    recursive_search = True
    include_paths = [os.getcwd()]

    verilog_files = find_verilog_files(target_directory, recursive=recursive_search)
    if not verilog_files:
        print(f"目录 '{target_directory}' 未找到任何 .v 文件。")
        return

    files_content = {file: open(file, encoding=detect_encoding(file)).readlines() for file in verilog_files}

    syntax_results = [
        check_verilog_syntax(file, include_paths=include_paths)
        for file in tqdm(verilog_files, desc="检查 Verilog 语法")
    ]

    repetition_scores = score_by_repetition(files_content)
    keyword_scores = score_by_keyword_occurrence(files_content)
    comment_ratio_scores = score_by_code_to_comment_ratio(files_content)
    length_diversity_scores = score_by_code_length_diversity(files_content)
    entropy_scores = score_by_information_entropy(files_content)

    results = []
    for result in syntax_results:
        file = result['file']
        overall_score = round((repetition_scores.get(file, 0) +
                                keyword_scores.get(file, 0) +
                                comment_ratio_scores.get(file, 0) +
                                length_diversity_scores.get(file, 0) +
                                entropy_scores.get(file, 0)) / 5, 2)

        # 修改为保留两位小数并且转换为百分比形式
        syntax_error_ratio = round(result['error_ratio'] * 100, 2)

        results.append({
            '文件名': file,
            '是否可运行': "是" if result['success'] else "否",
            '总行数': result['total_lines'],
            '语法错误行数': result['error_lines'],
            '语法错误比例': f"{syntax_error_ratio}%",
            '重复率评分': f"{repetition_scores.get(file, 0):.2f}",
            '关键词评分': f"{keyword_scores.get(file, 0):.2f}",
            '注释比例评分': f"{comment_ratio_scores.get(file, 0):.2f}",
            '长度多样性评分': f"{length_diversity_scores.get(file, 0):.2f}",
            '信息熵评分': f"{entropy_scores.get(file, 0):.2f}",
            '综合评分': f"{overall_score:.2f}"
        })

    df = pd.DataFrame(results)
    output_file = os.path.join(target_directory, 'verilog_analysis_results.xlsx')
    df.to_excel(output_file, index=False, sheet_name="分析结果")

    print(f"分析完成，结果已保存到文件：{output_file}")

if __name__ == "__main__":
    main()
