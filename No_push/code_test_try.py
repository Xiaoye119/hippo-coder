import os
import random
from difflib import SequenceMatcher
from collections import Counter
import re
import math
from statistics import stdev

# 定义关键词列表（可以根据实际需求调整）
# KEYWORDS = [
#     'module', 'endmodule', 'input', 'output', 'inout', 'wire', 'reg', 'integer',
#     'parameter', 'localparam', 'function', 'endfunction', 'task', 'endtask',
#     'if', 'else', 'case', 'casex', 'casez', 'default', 'for', 'while', 'repeat',
#     'always', 'initial', 'begin', 'end', 'fork', 'join', 'posedge', 'negedge',
#     'bit', 'logic', 'byte', 'shortint', 'int', 'longint', 'shortreal', 'chandle',
#     'string', 'enum', 'struct', 'union', 'typedef', 'signed', 'unsigned',
#     'interface', 'endinterface', 'modport', 'class', 'endclass', 'extends',
#     'implements', 'virtual', 'import', 'export', 'package',
#     'assert', 'assume', 'cover', 'expect', 'property', 'sequence',
#     'rand', 'randc', 'constraint', 'with', 'inside'
# ]

KEYWORDS = [
    'always', 'and', 'assign', 'begin', 'buf', 'bufif0', 'bufif1', 'case',
    'casex', 'casez', 'cmos', 'deassign', 'default', 'defparam', 'disable',
    'edge', 'else', 'end', 'endcase', 'endfunction', 'endmodule',
    'endprimitive', 'endspecify', 'endtable', 'endtask', 'event', 'for',
    'force', 'forever', 'fork', 'function', 'highz0', 'highz1', 'if', 'ifnone',
    'initial', 'inout', 'input', 'integer', 'join', 'large', 'macromodule',
    'medium', 'module', 'nand', 'negedge', 'nmos', 'nor', 'not', 'notif0',
    'notif1', 'or', 'output', 'parameter', 'pmos', 'posedge', 'primitive',
    'pull0', 'pull1', 'pulldown', 'pullup', 'rcmos', 'real', 'realtime', 'reg',
    'release', 'repeat', 'rnmos', 'rpmos', 'rtran', 'rtranif0', 'rtranif1',
    'scalared', 'small', 'specify', 'specparam', 'strength', 'strong0',
    'strong1', 'supply0', 'supply1', 'table', 'task', 'time', 'tran', 'tranif0',
    'tranif1', 'tri', 'tri0', 'tri1', 'triand', 'trior', 'trireg', 'vectored',
    'wait', 'wand', 'weak0', 'weak1', 'while', 'wire', 'wor', 'xnor', 'xor'
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




def score_by_keyword_occurrence(files_content):
    """根据关键词出现率打分."""
    # TODO 去掉注释，去掉标点
    scores = {}
    keyword_pattern = re.compile('|'.join(re.escape(kw) for kw in KEYWORDS))

    for filename, lines in files_content.items():
        cleaned_lines = []   # 去掉注释和标点后的行数据
        continue_content = [' ',"\n\n","\t","\n"]
        for line in lines:
            if line in continue_content:
                continue
            line = re.sub(r'//.*|/\*.*?\*/', '', line)  # 去掉单行和多行注释
            line = re.sub(r'[\W_]+', ' ', line)  # 去掉标点
            # line = re.sub(r'\s+', '', line)  # \s 匹配任何空白字符，包括空格、制表符、换行符等
            # if line:   # 去除数据中所有的''空字符串。
            cleaned_lines.append(line)
        content = ' '.join(cleaned_lines).lower()
        words = re.findall(r'\b\w+\b', content)
        matches = keyword_pattern.findall(content)
        total_keywords = len(matches)  # 包含重复的关键字总数
        unique_keywords = len(set(matches))  # 不重复的关键字总数
        total_words = len(words)

        if total_words == 0 or total_keywords == 0:
            score = 0
        else:
            ratio_diff = total_keywords / total_words   # 关键词在所有词中的比例 (包含重复)，关键词占比越高，得分越低，反映代码中关键词的密集程度。
            no_repeat = unique_keywords / total_keywords  # 不重复关键字在所有关键字中的比例，反应关键词的多样性。即代码是否重复使用相同关键词）
            # score = max((1 - ratio_diff) * 100,0)
            combined_ratio = 0.8 * (1 - ratio_diff) + 0.2 * no_repeat   # 融合公式
            score = max(combined_ratio * 100, 0)  # 将融合后的比例转换为百分制得分。

        scores[filename] = int(score)
    return scores
# 遇到的问题：去掉标点并用空格将字符进行连接以后，会将很多单个字比如i或r，还有单数字算进来，导致单词总数量变大，是否需要将这些去掉？




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

            # 优先处理多行注释块
            if block_comment:
                comment_lines += 1
                if '*/' in stripped_line:
                    block_comment = False
                    # 如果注释结束后还有代码，继续检测
                    stripped_line = stripped_line.split('*/', 1)[1].strip()
                else:
                    continue

            # 检测多行注释的开始
            if '/*' in stripped_line:
                before_comment, after_comment = stripped_line.split('/*', 1)
                if before_comment.strip():
                    code_lines += 1  # 注释前的代码部分计为代码行
                comment_lines += 1
                block_comment = True
                stripped_line = after_comment.split('*/', 1)[-1].strip() if '*/' in after_comment else ''
                if not stripped_line:
                    continue

            # 检测单行注释
            if '//' in stripped_line:
                before_comment, _ = stripped_line.split('//', 1)
                if before_comment.strip():
                    code_lines += 1  # 注释前的代码部分计为代码行
                comment_lines += 1
                continue

            # 剩余部分计为代码行
            if stripped_line:
                code_lines += 1

        total_lines = code_lines + comment_lines
        if total_lines == 0:
            score = 0
        else:
            score = (code_lines / total_lines) * 100  # 有效代码率越高得分越高

        scores[filename] = score
    return scores





def main():
    directory = "try_dataset"

    files_content = read_verilog_files(directory)

    # repetition_scores = score_by_repetition(files_content)
    keyword_scores = score_by_keyword_occurrence(files_content)
    code_comment_ratio_scores = score_by_code_to_comment_ratio(files_content)
    # code_length_diversity_scores = score_by_code_length_diversity(files_content)
    # information_entropy_scores = score_by_information_entropy(files_content)

    # print("重复程度评分：")
    # for filename, score in repetition_scores.items():
    #     print(f"文件名: {filename}, 评分: {score:.2f}")

    print("\n关键词出现率评分：")
    for filename, score in keyword_scores.items():
        print(f"文件名: {filename}, 评分: {score:.2f}")

    print("\n有效代码率评分：")
    for filename, score in code_comment_ratio_scores.items():
        print(f"文件名: {filename}, 评分: {score:.2f}")

    print("\n代码长度分布评分：")
    # for filename, score in code_length_diversity_scores.items():
    #     print(f"文件名: {filename}, 评分: {score:.2f}")
    #
    # print("\n单行信息熵评分：")
    # for filename, score in information_entropy_scores.items():
    #     print(f"文件名: {filename}, 评分: {score:.2f}")


if __name__ == "__main__":
    main()
