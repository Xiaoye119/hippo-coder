from typing import Dict, List, Optional, Tuple, Union
from transformers import AutoTokenizer, AutoModelForCausalLM, AutoModel
from transformers.generation.utils import GenerationConfig
from vllm import LLM, SamplingParams
import torch.cuda as cuda  
import json
from tqdm import tqdm  # 进度条库
import csv
from openpyxl import Workbook
import openpyxl

class BaseModel:
    def __init__(self, path: str = '') -> None:
        self.path = path
    
    def load_model(self, prompt:str, history: List[dict]) -> None:
        pass
    def chat(self) -> None:
        pass

class Qwen(BaseModel):
    def __init__(self, path: str = '', is_vllm: bool = False) -> None:
        super().__init__(path)
        self.is_vllm = is_vllm
        self.load_model()

    def load_model(self) -> None:
        print('================ Loading model ================')
        self.tokenizer = AutoTokenizer.from_pretrained(pretrained_model_name_or_path=self.path)
        if not self.is_vllm:
            self.model = AutoModelForCausalLM.from_pretrained(pretrained_model_name_or_path=self.path, 
                                                            torch_dtype="auto",
                                                            device_map="auto").eval()
        else:
            self.vllm_model = LLM(model=self.path, tensor_parallel_size=cuda.device_count(), dtype="float16", gpu_memory_utilization=0.8)
        
        print('================ Model loaded ================')
    
    def chat(self, messages:List[dict]) -> str:
        text = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        model_inputs = self.tokenizer([text], return_tensors='pt').to(self.model.device)
        generated_ids = self.model.generate(**model_inputs, max_new_tokens=512)
        generated_ids = [
            output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
        ]
        response = self.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
        return response
    
    def vllm_chat(self, messages:Union[List[Dict[str, str]], List[List[Dict[str, str]]]]) -> str:
        text = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, max_length=2048, truncation=True)
        sampling_params = SamplingParams(temperature=0.7, top_p=0.8, repetition_penalty=1.05, max_tokens=512)
        responses = self.vllm_model.generate(text, sampling_params)
        return responses
    
def extract_inputs(json_data,num_samples=10):
    input_list = []
    label_list = []
    for item in json_data:
        input_list.append(item['input'])
        label_list.append(item['output'])
    return input_list[:num_samples],label_list[:num_samples]

if __name__ == "__main__":
    # 定义模型和初始消息
    model = Qwen('/hy-tmp/hippo/models/Qwen2.5-Coder-7B', is_vllm=True)

    # 初始化结果列表
    querys = [] 
    outputs = []

    # 从文件中读取JSON数据
    with open('/hy-tmp/hippo/data/sft_data/hippo_test_sft_data.json', 'r') as file:
      json_data = json.load(file)

    questions,label_list = extract_inputs(json_data,num_samples=2000)

    # 遍历每个功效名词并生成 prompt
    for q in tqdm(questions, desc="处理进度"):
        # 将 prompt 添加到消息中
        messages = [{'role': 'user', 'content': q}]
        querys.append(messages)

    responses = model.vllm_chat(querys)
    for response in responses:
        generated_text = response.outputs[0].text
        outputs.append(generated_text)

    data = [
      ["问题", "标准答案", "base 预测答案"],
    ]

    for q,l,o in zip(questions, label_list, outputs):
        data.append([q,l,o])

    # 创建一个新的工作簿对象
    workbook = Workbook()
    # 获取默认的工作表
    sheet = workbook.active

    # 将数据逐行写入工作表中
    for row in data:
        sheet.append(row)

    # 保存工作簿为Excel文件（这里指定了保存路径和文件名，可以根据实际需求修改）
    workbook.save('/hy-tmp/hippo/hippo-coder/eval/hippo_eval_output.xlsx')

    print("数据写入完成！")

    # # 打开文件，使用 'w' 模式表示写入（如果文件不存在则创建，如果存在则覆盖）
    # with open('/hy-tmp/hippo/hippo-coder/eval/hippo_eval_output.csv', 'w', newline='', encoding='utf-8') as csvfile:
    #   writer = csv.writer(csvfile)
    #   # 逐行写入数据
    #   for row in data:
    #     writer.writerow(row)
