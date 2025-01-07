import os
import random
import numpy as np
import torch
import numpy as np
import tiktoken
import json
from tqdm import tqdm

def analyze_verilog_file(filename, lines, context_window=2):
    # 过滤掉空行和注释行
    lines = [line.strip() for line in lines if line.strip() and not line.strip().startswith('//')]

    line_lengths = [len(line) for line in lines]

    # 计算最短、最长、平均和中位数长度
    min_length = min(line_lengths)
    max_length = max(line_lengths)
    avg_length = np.mean(line_lengths)
    median_length = np.median(line_lengths)

    # 计算每行的关键词和标识符比率
    keyword_ratios = []
    identifier_ratios = []

    for line in lines:
        words = line.split()
        keyword_count = sum(1 for word in words if word in verilog_keywords)
        identifier_count = sum(1 for word in words if word.isidentifier() and word not in verilog_keywords)

        keyword_ratio = keyword_count / len(words) if len(words) > 0 else 0
        identifier_ratio = identifier_count / len(words) if len(words) > 0 else 0

        keyword_ratios.append(keyword_ratio)
        identifier_ratios.append(identifier_ratio)

    # 计算平均关键词和标识符比率
    avg_keyword_ratio = np.mean(keyword_ratios)
    avg_identifier_ratio = np.mean(identifier_ratios)

    # 构建结果字典
    file_name = os.path.basename(filename).replace('.v', '')
    result = {
        file_name: {
            'min_length': min_length,
            'max_length': max_length,
            'avg_length': avg_length,
            'median_length': median_length,
            'avg_keyword_ratio': avg_keyword_ratio,
            'avg_identifier_ratio': avg_identifier_ratio,
        }
    }

    return result
def read_verilog_files(directory, num):
    # 初始化字典
    verilog_dict = {}
    verilog_data_analyze = {}
    # 遍历指定目录下的所有文件
    for filename in os.listdir(directory)[:num]:
        # TODO 测试使用
        # if filename != 'example.v':
        #     continue
        if filename.endswith(".v"):
            # 去掉 .v 后缀作为字典的 key
            key = filename[:-2]
            filepath = os.path.join(directory, filename)
            # 读取文件内容并处理每一行
            with open(filepath, 'r', encoding='utf-8') as file:
                process_lines = [line.rstrip('\n') if len(line) > 0 else line for line in file.readlines()]
                verilog_dict[key] = process_lines
                # 数据统计
                verilog_data_analyze = analyze_verilog_file(filename, process_lines)
    return verilog_dict,verilog_data_analyze

def permute(
            sample,
            np_rng,
            suffix_tok_id,
            prefix_tok_id,
            middle_tok_id,
            pad_tok_id,
            mask_tok_id,
            fim_rate=0.5,
            fim_spm_rate=0.5,
            truncate_or_pad=False,
    ):
        """
        接收一个样本（token 列表）并以 fim_rate 的概率对其进行 FIM 转换，使用两种 FIM 模式：
        PSM 和 SPM（以 fim_spm_rate 的概率）。
        """
        # 多行
        boundaries = list(np_rng.randint(low=0, high=len(sample) + 1, size=2))  # 随机生成两个位置索引， 数值中间部分为 middle
        boundaries.sort()
        # 分前、中、割后,三部分
        prefix = np.array(sample[: boundaries[0]], dtype=np.int64)
        middle = np.array(sample[boundaries[0]: boundaries[1]], dtype=np.int64)
        suffix = np.array(sample[boundaries[1]:], dtype=np.int64)
        if np_rng.binomial(1, fim_spm_rate):
            # SPM (variant 2 from FIM paper)
            new_sample = np.concatenate(
                [
                    """
                    <p><s>
                    34
                    <m>
                    1
                    2
                    """
                    [prefix_tok_id, suffix_tok_id],
                    suffix,
                    [middle_tok_id],
                    prefix,
                    middle,
                ]
            )
        else:
            # PSM
            new_sample = np.concatenate(

                [
                    """
                    <p>
                    12
                    <s>
                    45
                    <m>
                    3
                    """
                    [prefix_tok_id],
                    prefix,
                    [suffix_tok_id],
                    suffix,
                    [middle_tok_id],
                    middle,
                ]
            )
        return list(new_sample), np_rng

if __name__ == '__main__':
    # 定义关键词列表
    verilog_keywords = [
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
    # 示例路径
    # directory = r"/home/tzb/hippo-coder/hippo-coder/data_mask"
    directory = r"/home/tzb/hippo-coder/hippo-coder/data_mask/a1_data"
    # 读取数据
    verilog_dict,verilog_data_analyze = read_verilog_files(directory, num=1300000)

    sft_datas_count = 100000
    """
    每一行都有采样 , 预测一行 40% , 两行-5行 30% , 比5行更多 10% , 剩下占 20% 搞单个字母 , 单个单词 , 多个单词 , 还有一行特别长就预测后边的几个字
    循环块 , 函数主体 , 比如感觉到明显是个冒泡 , 那多行直接给他补全了 , 可能不会很多 , 但是训练的时候得单独去抽函数块和循环快
    还有 if else 也得 , try catch , whele 循环 
    """
    datas_ratio = {
        "单行": int(sft_datas_count * 0.4),
        "多行": int(sft_datas_count * 0.3),
        "单字符预测单词": int(sft_datas_count * 0.2),
        "代码块": int(sft_datas_count * 0.1),
    }

    min_ideal_length = 5
    max_ideal_length = 80

    # 特殊字符
    FIM_PREFIX = "<fim-prefix>"
    FIM_MIDDLE = "<fim-middle>"
    FIM_SUFFIX = "<fim-suffix>"
    FIM_PAD = "<fim-pad>"
    FIM_MASK = "<fim-mask>"

    # bpe分词器
    tokenizer = tiktoken.get_encoding("gpt2")
    # In production, load the arguments directly instead of accessing private attributes
    # See openai_public.py for examples of arguments for specific encodings
    enc = tiktoken.Encoding(
        # If you're changing the set of special tokens, make sure to use a different name
        # It should be clear from the name what behaviour to expect.
        name="cl100k_base_im",
        pat_str=tokenizer._pat_str,
        mergeable_ranks=tokenizer._mergeable_ranks,
        special_tokens={
            **tokenizer._special_tokens,
            # 添加特殊字符
            FIM_PREFIX: 50300,
            FIM_MIDDLE: 50400,
            FIM_SUFFIX: 50500,
            FIM_PAD: 50600,
            FIM_MASK: 50700,
        })
    # 获取特殊符号id
    suffix_tok_id, prefix_tok_id, middle_tok_id, pad_tok_id,mask_tok_id = (enc._special_tokens[tok] for tok in [FIM_SUFFIX, FIM_PREFIX, FIM_MIDDLE, FIM_PAD, FIM_MASK])
    np_rng = np.random.RandomState(seed=0) # rng state for FIM
    datas = []
    num = 1000
    for key,value in tqdm(verilog_dict.items()):
        trunk_data = "".join(value)
        sample = enc.encode(trunk_data)
        tmp = permute(
            sample,
            np_rng,
            suffix_tok_id,
            prefix_tok_id,
            middle_tok_id,
            pad_tok_id,
            mask_tok_id,
            fim_rate=0.5,
            fim_spm_rate=0.5,
            truncate_or_pad=True,
        )
        data = enc.decode(tokens=tmp[0])
        # 找到 np.int64(50400) 的索引
        index = tmp[0].index(50400)
        # 使用列表推导式替换 np.int64(50400) 之后的所有内容为 np.int64(50700)
        mask_data_encode = tmp[0][:index + 1] + [np.int64(50700)] * (len(tmp[0]) - index - 1)
        mask_data = enc.decode(tokens=mask_data_encode)

        # 构建一个字典，其中包含原始数据和掩码数据
        data_dict = {
            "ori_data": data,
            "mask_data": mask_data
        }
        datas.append(data_dict)

    # 将字典按 jsonl 格式写入文件
    with open("output.jsonl", "w", encoding="utf-8") as f:
        for item in datas:
            # 将每个字典转换为 JSON 字符串并写入文件
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

