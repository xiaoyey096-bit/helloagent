"""
LLM 客户端: 封装对任何兼容 OpenAI 接口服务的流式调用,供智能体"思考"。

HelloAgentsLLM: LLM 客户端,配置从 .env 读取;think() 流式接收并返回完整回复,debug 参数控制打印原始 chunk 数据包
"""

import os
from openai import OpenAI
from dotenv import load_dotenv

# 加载 .env 环境变量(必须在读取 os.getenv 之前执行)
load_dotenv()


class HelloAgentsLLM:
    '''LLM 客户端:调用任何兼容 OpenAI 接口的服务,默认流式响应;model/apiKey/baseUrl/timeout 缺省读 .env,debug 控制打印原始 chunk。'''

    def __init__(self, model: str = None, apiKey: str = None, baseUrl: str = None,
                 timeout: int = None, debug: bool = False):
        '''
        初始化客户端。优先使用传入参数,未提供则从 .env 环境变量加载。
        '''
        self.model = model or os.getenv("LLM_MODEL_ID")
        self.debug = debug
        apiKey = apiKey or os.getenv("LLM_API_KEY")
        baseUrl = baseUrl or os.getenv("LLM_BASE_URL")
        timeout = timeout or int(os.getenv("LLM_TIMEOUT", 60))

        if not all([self.model, apiKey, baseUrl]):
            raise ValueError("模型ID、API密钥和服务地址必须被提供或在.env文件中定义。")

        self.client = OpenAI(api_key=apiKey, base_url=baseUrl, timeout=timeout)

    def think(self, messages: list[dict[str, str]], temperature: float = 0) -> str:
        '''流式调用大语言模型并返回完整响应,调用失败返回 None。'''
        print(f"正在调用 {self.model} 模型...")
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                stream=True,
            )

            # 处理流式响应:每个 chunk 形如
            # {"choices":[{"delta":{"content":"文本片段"},"finish_reason":null}]}
            print("已经成功建立流式连接,开始接收输出...")
            collected_content = []
            for chunk in response:
                if self.debug:
                    # =====打印原始数据包JSON(教学观察用)=====
                    print("\n====================原始chunk数据包====================")
                    print(chunk.model_dump_json(indent=2))
                    # ==========================================

                if not chunk.choices:   # 防止 choices[0] 取到空数据包导致报错
                    continue
                content = chunk.choices[0].delta.content or ""
                print(content, end="", flush=True)
                collected_content.append(content)
            print()  # 流式输出结束后换行
            return "".join(collected_content)   # 把['1','2','3']拼接成"123"

        except Exception as e:
            print(f"调用LLM API时发生错误: {e}")
            return None


# --- 客户端使用示例 ---
if __name__ == '__main__':
    try:
        llmClient = HelloAgentsLLM()

        exampleMessages = [
            {"role": "system", "content": "你是一个智能助手,帮我解决问题。"},
            {"role": "user", "content": "帮我写一个冒泡排序"}
        ]

        print("--- 调用LLM ---")
        responseText = llmClient.think(exampleMessages)
        if responseText:
            print("\n\n--- 完整的模型响应 ---")
            print(responseText)
        else:
            print("--- 模型未返回有效内容 ---")

    except ValueError as e:
        print(e)
