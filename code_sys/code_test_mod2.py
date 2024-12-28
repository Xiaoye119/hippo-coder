import hashlib
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
from openpyxl.styles import Alignment

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
    return verilog_files[:500]

# 运行和语法评分
def check_verilog_syntax(file_path, include_paths=None):
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

# 新增：行数评分函数
def score_by_line_count(total_lines):
    if total_lines < 10 or total_lines > 400:
        return None  # 排除不符合范围的文件
    return round(60 + (total_lines - 10) * 40 / (400 - 10), 2)


def calculate_similarity_ratio(str1, str2):
    """计算两段字符串的相似度比率."""
    return SequenceMatcher(None, str1, str2).ratio()

def score_by_repetition(files_content, n=10, sampleRate=0.3):
    # 整个文件的代码行数决定随机行数，设定个比例
    # 分组，设置块大小，随机抽取块比对
    # 分组，设按照上面的分组，计算交叉数，交叉数多的给更高的
    # 迷你哈希计算相似度，minihash，行和行相比
    """根据重复程度打分."""
    scores = {}
    for filename, lines in files_content.items():

        """1.0 随机抽n行，n行内 每两行逐个计算重复分，时间复杂度O(n²)"""
        # sampled_lines = random.sample(lines, min(n, len(lines)))
        """2.0 按比例采样"""
        currLinesNum = len(lines)
        sampleLinesNum = int(currLinesNum * sampleRate)
        sampled_lines = random.sample(lines, max(1, sampleLinesNum))

        similarity_scores = []
        for i in range(len(sampled_lines)):
            for j in range(i + 1, len(sampled_lines)):
                ratio = calculate_similarity_ratio(sampled_lines[i], sampled_lines[j])
                similarity_scores.append(ratio)

        avg_similarity = sum(similarity_scores) / (len(similarity_scores) or 1)
        # 将相似度转换为分数，这里我们假设完全不相似得100分，完全相同得0分
        score = max(0, 100 - avg_similarity * 100)


        """3.0 分块"""
        # truncatingRate = 0.1
        # chunkSize = int(len(lines) * truncatingRate) or 1
        # chunkNum = len(lines) // chunkSize
        # if chunkNum < 2:
        #     continue

        """4.0 交叉分组"""

        """5.0 MiniHash"""
        # 存储每行的哈希值
        hashes = set()
        duplicates = 0

        # 遍历每行，计算MiniHash并检测是否重复
        for line in lines:
            line = line.strip()  # 去掉行尾的换行符和空格
            if line:  # 排除空行
                hash_value = hashlib.sha256(line.encode('utf-8')).hexdigest()
                if hash_value in hashes:
                    duplicates += 1
                else:
                    hashes.add(hash_value)
        # 计算行间重复度
        dulicateRatio = duplicates / currLinesNum if currLinesNum > 0 else 0
        score = (1 - dulicateRatio) * 100

        scores[filename] = score

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
            # 计算关键字比例
            actual_ratio = total_keywords / total_words
            # 理想关键字比例范围
            ideal_min_ratio = 0.05  # 最低理想比例
            ideal_max_ratio = 0.20  # 最高理想比例

            # 偏离理想范围的惩罚
            if actual_ratio < ideal_min_ratio:
                penalty = (ideal_min_ratio - actual_ratio) * 100
                ratio_score = max(100 - penalty, 0)
            elif actual_ratio > ideal_max_ratio:
                penalty = (actual_ratio - ideal_max_ratio) * 100
                ratio_score = max(100 - penalty, 0)
            else:
                # 在合理范围内得满分
                ratio_score = 100.0

            # 计算唯一关键字比例得分
            no_repeat = unique_keywords / total_keywords
            unique_score = no_repeat * 100

            # 综合得分，增加关键字总量的影响
            total_keyword_weight = min(total_keywords / 100, 1.0)  # 关键字总量对分数的权重（100 个关键字以上权重为 1）
            score = 0.6 * ratio_score + 0.3 * unique_score + 0.1 * (total_keyword_weight * 100)

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
            # 设定合理的代码与注释比例范围，例如 3:1 到 5:1
            ideal_ratio_min = 3 / 4  # 最低合理比例
            ideal_ratio_max = 5 / 6  # 最高合理比例
            actual_ratio = code_lines / total_lines

            if actual_ratio < ideal_ratio_min:
                # 注释过多，惩罚得分
                penalty = (ideal_ratio_min - actual_ratio) * 100
                score = max(100 - penalty, 0)
            elif actual_ratio > ideal_ratio_max:
                # 注释过少，惩罚得分
                penalty = (actual_ratio - ideal_ratio_max) * 100
                score = max(100 - penalty, 0)
            else:
                # 在合理范围内，满分
                score = 100.0

        scores[filename] = round(score, 2)  # 保留两位小数
    return scores

# 长度分布率评分
# TODO 理想长度、最大、最小理想行数根据现在文件的实际情况计算
# TODO lengths长度的计算逻辑，不能按照字符，按照空格切分
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

# 单行信息熵评分
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

# 评分函数定义
def calculate_similarity_ratio(str1, str2):
    return SequenceMatcher(None, str1, str2).ratio()


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
    total_score_sum = 0  # 总分数
    total_files = len(verilog_files)  # 文件数量

    for result in syntax_results:
        file = result['file']

        # 语法错误比例评分：100 - 错误比例（语法错误比例越低，得分越高）
        syntax_error_ratio_score = max(0, 100 - result['error_ratio'] * 100)

        # 可否运行得分：如果文件能运行（没有语法错误），得100分，否则得0分
        run_score = 100 if result['success'] else 0

        # 综合评分 = 各项评分 + 语法错误比例评分 + 可否运行得分
        overall_score = round((repetition_scores.get(file, 0) +
                               keyword_scores.get(file, 0) +
                               comment_ratio_scores.get(file, 0) +
                               length_diversity_scores.get(file, 0) +
                               entropy_scores.get(file, 0) +
                               syntax_error_ratio_score + run_score) / 7, 2)

        # 统计总分
        total_score_sum += overall_score

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
            '语法错误比例评分': f"{syntax_error_ratio_score:.2f}",
            '可否运行得分': f"{run_score:.2f}",
            '综合评分': f"{overall_score:.2f}"
        })

    # 计算平均分
    average_score = round(total_score_sum / total_files, 2) if total_files > 0 else 0

    # 输出到 DataFrame
    df = pd.DataFrame(results)
    output_file = os.path.join(target_directory, 'verilog_analysis_results.xlsx')

    # 添加总分和平均分
    summary = pd.DataFrame([{
        '文件名': '总计',
        '总得分': f"{total_score_sum:.2f}",
        '平均分': f"{average_score:.2f}"
    }])

    # 将分析结果和汇总数据写入同一工作簿
    with pd.ExcelWriter(output_file) as writer:
        df.to_excel(writer, index=False, sheet_name="分析结果")
        summary.to_excel(writer, index=False, sheet_name="总分与平均分")

        # 获取工作簿和工作表
        workbook = writer.book
        worksheet = workbook['分析结果']

        # 设置居中对齐
        for row in worksheet.iter_rows():
            for cell in row:
                cell.alignment = Alignment(horizontal='center', vertical='center')  # 居中对齐

        # 同样为汇总表设置居中
        summary_sheet = workbook['总分与平均分']
        for row in summary_sheet.iter_rows():
            for cell in row:
                cell.alignment = Alignment(horizontal='center', vertical='center')  # 居中对齐

    print(f"分析完成，结果已保存到文件：{output_file}")


if __name__ == "__main__":
    main()
