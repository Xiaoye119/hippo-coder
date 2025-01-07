import os
import re
import random
import shutil
import subprocess
import chardet
import math
from tqdm import tqdm
import pandas as pd
from difflib import SequenceMatcher
from collections import Counter
from statistics import stdev
from concurrent.futures import ThreadPoolExecutor, as_completed
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
    return verilog_files[:]

# 运行和语法评分
def check_verilog_syntax(file_path, include_paths=None):
    try:
        cmd = ["iverilog", "-t", "null"]
        if include_paths:
            for path in include_paths:
                cmd.extend(["-I", path])
        cmd.append(file_path)

        process = subprocess.run(cmd, stderr=subprocess.PIPE, text=True, check=True)
        with open(file_path, "r", encoding=detect_encoding(file_path) or 'utf-8') as file:
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

        with open(file_path, "r", encoding=detect_encoding(file_path) or 'utf-8') as file:
            total_lines = sum(1 for _ in file)

        error_count = len(error_lines)
        error_ratio = error_count / total_lines if total_lines > 0 else 0

        return {
            "file": file_path,
            "success": False,
            "total_lines": total_lines,
            "error_lines": error_count,
            "error_ratio": error_ratio,
            "errors": e.stderr.strip()
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

# 并行化语法检查
def check_verilog_syntax_parallel(files, include_paths=None):
    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(check_verilog_syntax, file, include_paths): file for file in files}
        results = []
        for future in tqdm(as_completed(futures), total=len(files), desc="检查 Verilog 语法"):
            results.append(future.result())
        return results

# 计算两个字符串的相似度
def calculate_similarity_ratio(line1, line2):
    return SequenceMatcher(None, line1, line2).ratio()

# 简单的归一化处理
def normalize_code(line):
    line = re.sub(r'\d+', 'NUM', line)  # 将所有数字替换成 'NUM'
    line = re.sub(r'[a-zA-Z]+', 'VAR', line)  # 将所有字母替换成 'VAR'
    return line

# 根据重复程度打分
def score_by_repetition(files_content, n=10, sampleRate=0.3):
    scores = {}
    for filename, lines in files_content.items():
        sampled_lines = random.sample(lines, max(1, int(len(lines) * sampleRate)))
        normalized_lines = [normalize_code(line.strip()) for line in sampled_lines]
        similarity_scores = [calculate_similarity_ratio(normalized_lines[i], normalized_lines[j])
                             for i in range(len(normalized_lines)) for j in range(i + 1, len(normalized_lines))]
        avg_similarity = sum(similarity_scores) / (len(similarity_scores) or 1)
        scores[filename] = max(0, (1 - avg_similarity) * 100)
    return scores

# 根据关键字出现率打分
def score_by_keyword_occurrence(files_content):
    scores = {}
    keyword_pattern = re.compile('|'.join(re.escape(kw) for kw in KEYWORDS))

    for filename, lines in files_content.items():
        cleaned_lines = [re.sub(r'//.*|/\*.*?\*/', '', line) for line in lines if line.strip()]
        content = ' '.join(cleaned_lines).lower()
        words = re.findall(r'\b\w+\b', content)
        matches = keyword_pattern.findall(content)
        total_keywords = len(matches)
        unique_keywords = len(set(matches))
        total_words = len(words)

        if total_words == 0 or total_keywords == 0:
            score = 0.0
        else:
            actual_ratio = total_keywords / total_words
            ideal_min_ratio = 0.02
            ideal_max_ratio = 0.1

            if actual_ratio < ideal_min_ratio:
                penalty = (ideal_min_ratio - actual_ratio) * 150
                ratio_score = max(100 - penalty, 0)
            elif actual_ratio > ideal_max_ratio:
                penalty = (actual_ratio - ideal_max_ratio) * 150
                ratio_score = max(100 - penalty, 0)
            else:
                ratio_score = 100.0

            no_repeat = unique_keywords / total_keywords if total_keywords > 0 else 0
            unique_score = no_repeat * 100

            control_keywords = ['if', 'else', 'case', 'for', 'while', 'repeat', 'always', 'initial']
            control_keyword_counts = Counter(re.findall(r'\b(?:' + '|'.join(control_keywords) + r')\b', content))
            control_diversity = len([1 for kw in control_keywords if control_keyword_counts[kw] > 0])
            control_score = min(control_diversity * 15, 100)

            score = 0.4 * ratio_score + 0.3 * unique_score + 0.3 * control_score

        scores[filename] = round(score, 2)
    return scores

# 根据代码与注释比例打分
def score_by_code_to_comment_ratio(files_content):
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
            elif '/*' in stripped_line:
                comment_lines += 1
                block_comment = True
            elif '//' in stripped_line:
                comment_lines += 1
            else:
                code_lines += 1

        total_lines = code_lines + comment_lines
        if total_lines == 0:
            score = 0.0
        else:
            actual_ratio = code_lines / total_lines
            ideal_ratio_min = 0.7
            ideal_ratio_max = 0.85

            if actual_ratio < ideal_ratio_min:
                penalty = (ideal_ratio_min - actual_ratio) * 100 * 2
                score = max(100 - penalty, 0)
            elif actual_ratio > ideal_ratio_max:
                penalty = (actual_ratio - ideal_ratio_max) * 100 * 2
                score = max(100 - penalty, 0)
            else:
                score = 100.0

        scores[filename] = round(score, 2)
    return scores

# 根据代码长度多样性打分
def score_by_code_length_diversity(files_content):
    scores = {}
    for filename, lines in files_content.items():
        lines = [line for line in lines if line.strip() and not line.strip().startswith("//") and "/*" not in line]
        lengths = [len(line.strip().split()) for line in lines if line.strip()]

        if not lengths:
            scores[filename] = 0.00
            continue

        length_stddev = stdev(lengths) if len(lengths) >= 2 else 0
        max_diff = max(lengths) - min(lengths)
        avg_length_diff = sum(abs(length - (sum(lengths) / len(lengths))) for length in lengths) / len(lengths)

        diversity_score = min(50, length_stddev * 10)
        diff_score = min(30, max_diff * 1.5)
        avg_diff_score = min(20, avg_length_diff * 2)

        diversity_weighted_score = diversity_score + diff_score + avg_diff_score
        score = max(0, min(100, diversity_weighted_score))

        scores[filename] = round(score, 2)
    return scores

# 根据信息熵打分
def score_by_information_entropy(files_content):
    def calculate_entropy(elements):
        if not elements:
            return 0
        counter = Counter(elements)
        probabilities = [count / len(elements) for count in counter.values()]
        return -sum(p * math.log2(p) for p in probabilities)

    scores = {}
    for filename, lines in files_content.items():
        entropies = []
        for line in lines:
            stripped_line = line.strip()
            if not stripped_line or stripped_line.startswith("//") or "/*" in stripped_line:
                continue

            char_entropy = calculate_entropy(stripped_line.replace(" ", ""))
            word_entropy = calculate_entropy(stripped_line.split())
            entropies.append((char_entropy, word_entropy))

        if not entropies:
            scores[filename] = 0.00
            continue

        avg_char_entropy = sum(char_entropy for char_entropy, _ in entropies) / len(entropies)
        avg_word_entropy = sum(word_entropy for _, word_entropy in entropies) / len(entropies)
        score = (avg_char_entropy + avg_word_entropy) / 2 * 20
        scores[filename] = round(min(100, score), 2)
    return scores

# 行数评分函数
def score_by_line_count(total_lines):
    if total_lines < 10 or total_lines > 400:
        return None  # 排除不符合范围的文件

    # 线性映射：将 [10, 400] 映射到 [20, 100]
    min_lines = 10
    max_lines = 400
    min_score = 20
    max_score = 100

    # 计算分数
    score = min_score + (max_score - min_score) * (total_lines - min_lines) / (max_lines - min_lines)
    return round(score, 2)

# 主函数
def main():
    if not check_iverilog_installed():
        exit(1)

    target_directory = os.path.join(os.getcwd(), "code-verilog")
    selected_directory = os.path.join(os.getcwd(), "Selected")

    if os.path.exists(selected_directory):
        shutil.rmtree(selected_directory)
    os.makedirs(selected_directory)

    verilog_files = find_verilog_files(target_directory, recursive=True)
    if not verilog_files:
        print(f"目录 '{target_directory}' 未找到任何 .v 文件。")
        return

    # 限制读取的文件数量为 n 个
    verilog_files = verilog_files[:]

    # 缓存文件内容
    files_content = {}
    for file in tqdm(verilog_files, desc="读取文件内容", unit="文件"):
        with open(file, "r", encoding=detect_encoding(file) or 'utf-8') as f:
            files_content[file] = f.readlines()

    # 并行化语法检查
    syntax_results = check_verilog_syntax_parallel(verilog_files, include_paths=[os.getcwd()])

    # 并行化评分计算
    with ThreadPoolExecutor() as executor:
        repetition_future = executor.submit(score_by_repetition, files_content)
        keyword_future = executor.submit(score_by_keyword_occurrence, files_content)
        comment_ratio_future = executor.submit(score_by_code_to_comment_ratio, files_content)
        length_diversity_future = executor.submit(score_by_code_length_diversity, files_content)
        entropy_future = executor.submit(score_by_information_entropy, files_content)

        repetition_scores = repetition_future.result()
        keyword_scores = keyword_future.result()
        comment_ratio_scores = comment_ratio_future.result()
        length_diversity_scores = length_diversity_future.result()
        entropy_scores = entropy_future.result()

    # 综合评分
    results = []
    total_score_sum = 0
    total_files = len(verilog_files)

    for result in syntax_results:
        file = result['file']
        syntax_error_ratio_score = max(0, 100 - result['error_ratio'] * 100)
        run_score = 60 if result['success'] else 50

        repetition_score = repetition_scores.get(file, 0)
        keyword_score = keyword_scores.get(file, 0)
        comment_ratio_score = comment_ratio_scores.get(file, 0)
        length_diversity_score = length_diversity_scores.get(file, 0)
        entropy_score = entropy_scores.get(file, 0)
        line_score = score_by_line_count(result['total_lines']) or 0  # 行数评分

        overall_score = round((repetition_score + keyword_score + comment_ratio_score +
                               length_diversity_score + entropy_score +
                               syntax_error_ratio_score + run_score + line_score) / 8, 2)

        total_score_sum += overall_score

        if overall_score > 50:
            shutil.copy(file, os.path.join(selected_directory, os.path.basename(file)))

        results.append({
            '文件名': file,
            '是否可运行': "是" if result['success'] else "否",
            '总行数': result['total_lines'],
            '语法错误行数': result['error_lines'],
            '语法错误比例': f"{result['error_ratio'] * 100:.2f}%",
            '重复率评分': f"{repetition_score:.2f}",
            '关键词评分': f"{keyword_score:.2f}",
            '注释比例评分': f"{comment_ratio_score:.2f}",
            '长度多样性评分': f"{length_diversity_score:.2f}",
            '信息熵评分': f"{entropy_score:.2f}",
            '行数评分': f"{line_score:.2f}",
            '语法错误比例评分': f"{syntax_error_ratio_score:.2f}",
            '可否运行得分': f"{run_score:.2f}",
            '综合评分': f"{overall_score:.2f}"
        })

    # 输出结果
    average_score = round(total_score_sum / total_files, 2) if total_files > 0 else 0
    df = pd.DataFrame(results)
    output_file = os.path.join(target_directory, 'verilog_analysis_results.xlsx')

    # 使用 tqdm 显示写入 Excel 文件的进度
    with pd.ExcelWriter(output_file) as writer:
        with tqdm(total=2, desc="写入 Excel 文件", unit="步骤") as pbar:
            df.to_excel(writer, index=False, sheet_name="分析结果")
            pbar.update(1)  # 更新进度条

            pd.DataFrame(
                [{'文件名': '总计', '总得分': f"{total_score_sum:.2f}", '平均分': f"{average_score:.2f}"}]).to_excel(
                writer, index=False, sheet_name="总分与平均分")
            pbar.update(1)  # 更新进度条

        # 设置单元格居中对齐
        workbook = writer.book
        worksheet = workbook['分析结果']
        for row in worksheet.iter_rows():
            for cell in row:
                cell.alignment = Alignment(horizontal='center', vertical='center')

        summary_sheet = workbook['总分与平均分']
        for row in summary_sheet.iter_rows():
            for cell in row:
                cell.alignment = Alignment(horizontal='center', vertical='center')

    # 使用 tqdm 显示复制文件的进度
    if results:
        selected_files = [result['文件名'] for result in results if float(result['综合评分']) > 50]
        with tqdm(total=len(selected_files), desc="复制文件到 Selected 文件夹", unit="文件") as pbar:
            for file in selected_files:
                shutil.copy(file, os.path.join(selected_directory, os.path.basename(file)))
                pbar.update(1)  # 更新进度条

    print(f"分析完成，结果已保存到文件：{output_file}")
    print(f"总分高于 50 分的文件已保存到文件夹：{selected_directory}")

if __name__ == "__main__":
    main()