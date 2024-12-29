# coding=utf-8
"""
@Author: Jacob Y
@Date  : 12/29/2024
@Desc  : 
"""
import os
import json
import re
import chardet
import codecs
# from pygments.lexers import guessLexerForFilename
import math

from tqdm import tqdm


def countLines(filePaths: list):
    totalLines = 0
    for filePath in filePaths:
        lines = read_data(filePath)
        totalLines += len(lines)
    return totalLines


# def detectLanguage(filePath):
#     with open(filePath, 'r', encoding=detect_encoding(filePath)) as f:
#         code = f.read()
#     lexer = guessLexerForFilename(filePath, code)
#     return lexer.name


def detect_encoding(filePath):
    with open(filePath, 'rb') as f:
        rawdata = f.read()
    return chardet.detect(rawdata)['encoding']


def read_data(filePath):
    try:
        with open(filePath, encoding=detect_encoding(filePath)) as f:
            return f.readlines()
    except Exception as e:
        print("文件编码格式错误", e)
        encoding = input("请输入您的文件编码格式")
        with open(filePath, encoding=encoding) as f:
            return f.readlines()
    # try:
    #     with open(filePath,encoding="utf-8") as f:
    #         return f.readlines()
    # except:
    #     try:
    #         with open(filePath, encoding="gbk") as f:
    #             return f.readlines()
    #     except:
    #         try:
    #             with open(filePath, encoding="gbk-2312") as f:
    #                 return f.readlines()
    #         except:
    #             return None


def strip_comments(codeFile):
    with open(codeFile, 'r', encoding="utf-8") as f:
        content = f.readlines()

    multiLine_commentPattern = r'/\*[^*]*\*+(?:[^/*][^*]*\*+)*/'
    singleLine_commentPattern = r'//.*'

    stripped_content = []

    # 将内容合并为一个字符串，然后用正则表达式替换多行和单行注释。
    joined_content = ''.join(content)

    multiLine_commentReplaced_content = re.sub(multiLine_commentPattern, '', joined_content)
    finalReplaced_content = re.sub(singleLine_commentPattern, '', multiLine_commentReplaced_content)

    replacedLines = joined_content.split('\n')

    # 对于多行注释，如果替换的注释行数超过20行，那么这些注释将被删除。
    # 对于单行注释，我们删除连续超过20行的注释。
    if len(replacedLines) - len(finalReplaced_content.split('\n')) > 20:
        # 返回替换了多行注释或超过20行的单行注释的内容。
        stripped_content = finalReplaced_content.split('\n')
    else:
        # 返回原内容
        stripped_content = content

    return stripped_content


def get_allFilePaths(directory):
    filePaths = []  # List to store file paths
    for root, directories, files in os.walk(directory):
        for filename in files:
            # Join the two strings to form the full filepath.
            filepath = os.path.join(root, filename)

            filePaths.append(filepath)  # Add it to the list.
    return filePaths


def splitFile(filePath, window, minLines=20, maxLines=30):
    lines = read_data(filePath)
    if not lines:
        return None

    # print('lines:', len(lines), filePath)
    # print("*" * 100)

    # maxLines = 20  # 每个切片的最大行数

    # chunks = list(more_itertools.windowed(lines, maxLines))
    chunks = []
    for i in range(0, len(lines), window):
        chunk = lines[i:i + maxLines]
        if len(chunk) < minLines:
            break
        else:
            print(len(chunk))

        chunks.append(''.join(chunk))

    return chunks


if __name__ == "__main__":
    codeDir = "../data/code-verilog"  # 代码文件路径
    outputDir = "./output2"
    txtFiles = get_allFilePaths(codeDir)  # 获取所有文件地址
    # print(txtFiles)

    if not os.path.exists(outputDir):
        os.mkdir(outputDir)

    # 分块参数设置
    maxLines = 30
    minLines = 20
    window = 5

    n = 0
    with open(os.path.join(outputDir, '/splitResult.jsonl'), 'w', encoding="utf-8") as outfile:
        for txtFile in tqdm(txtFiles):
            # print(txtFile)
            chunks = splitFile(txtFile, window, minLines=minLines, maxLines=maxLines)  # 切分获取case
            if chunks:
                for chunk in chunks:
                    jsonRecord = {"language": "verilog", "code": chunk}
                    outfile.write(json.dumps(jsonRecord, ensure_ascii=False) + "\n")
                    n += 1
    print(f"items:{n}")