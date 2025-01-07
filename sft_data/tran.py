"""
将文件1中的数据转化为目标格式,生成文件2，给出 python 代码的实现
文件1为 :
```
{
    "language": "verilog",
    "prefix": "assign z9 =",
    "middle": "1'b0; assign z8 = ~x3;",
    "suffix": "endmodule",
    "block_id": "block_id_4_2",
    "file_name": "5xp1_FPGA_102_0.v"
}

{
    "language": "verilog",
    "prefix": "// Benchmark \"FAU\" written by ABC on Thu Jul 30 19:26:48 2020\n\nmodule FAU ( \n    x0, x1, x2, x3, x4, x5, x6,\n    z0, z1, z2, z3, z4, z5, z6, z7, z8, z9  );",
    "middle": "  input  x0, x1, x2, x3, x4, x5, x6;",
    "suffix": "  output z0, z1, z2, z3, z4, z5, z6, z7, z8, z9;",
    "block_id": "block_id_5_1",
    "file_name": "5xp1_FPGA_102_1.v"
}
```
目标格式为 :
```
[
  {
    "instruction": "",
    "input": "<|fim_prefix|>assign z9 =<|fim_suffix|>endmodule<|fim_middle|>",
    "output": "1'b0; assign z8 = ~x3;"
  },
  {
    "instruction": "",
    "input": "<|fim_prefix|>// Benchmark \"FAU\" written by ABC on Thu Jul 30 19:26:48 2020\n\nmodule FAU ( \n    x0, x1, x2, x3, x4, x5, x6,\n    z0, z1, z2, z3, z4, z5, z6, z7, z8, z9  );<|fim_suffix|>  output z0, z1, z2, z3, z4, z5, z6, z7, z8, z9;<|fim_middle|>",
    "output": "  input  x0, x1, x2, x3, x4, x5, x6;"
  }
]
```
"""

import json
import random


def transform_data(input_file, output_file):
    result = []
    with open(input_file, 'r') as f:
        data = f.read().strip().split('\n\n')  # 按两个换行符分割每个原始数据块
        if len(data) >= 12000:
            data = data[:12000]  # 抽取12000条数据
        for item_str in data:
            item = json.loads(item_str)
            # 以50%的概率决定output的取值方式
            if random.random() < 0.5:
                new_item = {
                    "instruction": "",
                    "input": f"<|fim_prefix|>{item['prefix']}<|fim_suffix|>{item['suffix']}<|fim_middle|>",
                    "output": item['middle']
                }
            else:
                new_item = {
                    "instruction": "",
                    "input": f"<|fim_prefix|>{item['prefix']}<|fim_suffix|>{item['suffix']}<|fim_middle|>",
                    "output": item['middle']
                }
            result.append(new_item)

    print(f"共处理 {len(result)} 条数据")
    with open(output_file, 'w') as f_out:
        json.dump(result, f_out, indent=2)


if __name__ == "__main__":
    # n = 12000
    # input_file = r"F:\hippo-coder-best\hippo-coder\data\train.jsonl"
    # output_file = "hippo_train_sft_data.txt"

    # 数据量
    n = 2000
    input_file = r"F:\hippo-coder-best\hippo-coder\data\test.jsonl"
    output_file = "hippo_test_sft_data.txt"

    transform_data(input_file, output_file)