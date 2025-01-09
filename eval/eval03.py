# coding=utf-8
"""
@Author: Jacob Y
@Date  : 1/8/2025
@Desc  : 
"""
import re
import pandas as pd
from tqdm import tqdm
from rouge_score import rouge_scorer
import hashlib
from datetime import datetime
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction


def preprocess_text(text):
    # 去除多余的空格和换行符
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# 计算 BLEU 分数【开源】
# def calculate_bleu(pred_text, label_text):
#     pred_tokens = preprocess_text(pred_text).split()
#     label_tokens = preprocess_text(label_text).split()
#
#     # 计算 BLEU 分数，简易版
#     common_tokens = set(pred_tokens) & set(label_tokens)
#     bleu_score = len(common_tokens) / len(label_tokens) if label_tokens else 0
#     return bleu_score

def calculate_bleu_score(candidate, reference):
    """
    使用 NLTK 的 sentence_bleu 函数计算 BLEU 分数，结合平滑函数和降低 n-gram 阶数。
    :param candidate: 候选文本（生成的文本）。
    :param reference: 参考文本（标准答案）。
    :return: BLEU 分数。
    """
    # 将文本分割为单词列表
    candidate_tokens = candidate.split()
    reference_tokens = reference.split()

    # 设置权重，仅计算 1-gram 和 2-gram
    weights = (0.5, 0.5, 0, 0)  # 1-gram 和 2-gram 的权重分别为 0.5，3-gram 和 4-gram 的权重为 0

    # 使用平滑函数
    smoothing_function = SmoothingFunction().method1  # 选择平滑方法

    # 计算 BLEU 分数
    score = sentence_bleu([reference_tokens], candidate_tokens, weights=weights, smoothing_function=smoothing_function) * 100
    return score

def calculate_window_hashes(code, window_size=10, hash_algorithm="sha256"):
    """
    计算代码片段的滑动窗口哈希值
    """
    window_hashes = []
    for i in range(len(code) - window_size + 1):
        window = code[i:i + window_size]
        hasher = hashlib.new(hash_algorithm)
        hasher.update(window.encode("utf-8"))
        window_hashes.append(hasher.hexdigest())
    return window_hashes

def calculate_similarity(code1, code2, window_size=3):
    """
    计算两段代码的局部相似度
    """
    # 计算滑动窗口哈希值
    hashes1 = calculate_window_hashes(code1, window_size)
    hashes2 = calculate_window_hashes(code2, window_size)

    # 统计重合的窗口数量
    common_hashes = set(hashes1).intersection(set(hashes2))
    common_count = len(common_hashes)

    # 计算相似度
    total_windows = max(len(hashes1), len(hashes2))
    similarity = common_count / total_windows if total_windows > 0 else 0
    return similarity


# 综合评分函数【设定权重】
def calculate_final_score(bleu_score, rouge_score, custom_score):
    """
    综合评分机制：
    - BLEU 占 20%
    - ROUGE 占 20%
    - 自定义评分占 60%
    """
    return 0.2 * bleu_score + 0.2 * rouge_score + 0.6 * custom_score


# 自定义打分函数
def custom_scoring(prediction, label, threshold_ratio=0.3):
    """
    自定义打分函数，根据前30%的匹配情况和错误数量计算分数
    """
    # 如果完全匹配，得1分
    if prediction == label:
        return 100

    # 计算前30%的字符长度【取较短的一方】
    threshold_length = int(min(len(prediction), len(label)) * threshold_ratio)
    pred_prefix = prediction[:threshold_length]
    label_prefix = label[:threshold_length]

    # 如果前30%完全匹配，得1分
    if pred_prefix == label_prefix:
        return 100

    similarity = calculate_similarity(pred_prefix, label_prefix)

    return similarity * 100

# 计算总分数
def calculate_total_scores(predictions, labels):
    """
    计算每一对 prediction 和 label 的总分数
    """
    scores = []  # 用于存储每条数据的综合评分

    rouge = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)

    for idx, (pred, label) in tqdm(enumerate(zip(predictions, labels), start=1),
                            total=len(predictions), desc="Calculating scores ..."):

        # 计算当前数据的 BLEU 分数
        # bleu_score = sentence_bleu([pred.split()], label.split()) * 100
        # bleu_score = calculate_bleu(pred, label) * 100

        bleu_score = calculate_bleu_score(pred, label)

        # 计算当前数据的 ROUGE 分数
        rouge_score = rouge.score(pred, label)['rougeL'].fmeasure * 100

        # 计算当前数据的自定义评分
        custom_score = custom_scoring(pred, label)

        # 计算当前数据的综合评分
        final_score = calculate_final_score(bleu_score, rouge_score, custom_score)
        scores.append(final_score)

        # 打印当前数据的评分
        # print(f"第 {idx} 条数据生成完成，当前评分:")
        # print(f"  - BLEU Score: {bleu_score:.2f}")
        # print(f"  - ROUGE-L Score: {rouge_score:.2f}")
        # print(f"  - Custom Score: {custom_score:.2f}")
        # print(f"  - Final Combined Score: {final_score:.2f}")

        # 计算最终平均分
    avg_final_score = sum(scores) / len(scores)
    print(f"最终平均综合评分: {avg_final_score:.2f}")
    return scores





if __name__ == '__main__':
    inputFile = r"hippo_eval_output_3083_trained.xlsx"

    timeStamp = datetime.now().strftime("%m-%d-%H%M")
    outputFile = rf"./eval_scores{timeStamp}.xlsx"

    df = pd.read_excel(inputFile)
    labels = df["标准答案"].astype(str)
    predictions = df['base 预测答案'].astype(str)
    # 运行评测
    print("开始评测...")
    scores = calculate_total_scores(predictions, labels)

    df['scores'] = scores
    df.to_excel(outputFile)
    print(f"评测完毕,文件已存储至{outputFile}")