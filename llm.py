"""
统一的大语言模型(LLM)客户端。

功能: 封装对任何兼容 OpenAI 接口服务的调用,默认流式输出,支持打印原始 chunk 数据包用于教学调试。
创建日期: 2026-08-15

输入:
  .env 环境变量: LLM_API_KEY / LLM_MODEL_ID / LLM_BASE_URL / LLM_TIMEOUT(可被构造参数覆盖)
  think() 方法入参: messages 消息列表,如 [{"role": "user", "content": "..."}]

输出:
  ① think() 返回模型完整回复字符串(流式收集拼接;调用失败返回 None)
  ② debug=True 时,控制台额外逐包打印每个原始 chunk 的 JSON(教学观察用)

核心类:
  HelloAgentsLLM — LLM 客户端,合并自 CLclient 与原教学 demo,debug 参数控制原始数据包打印
"""

import os
from openai import OpenAI
from dotenv import load_dotenv

# 加载 .env 环境变量(必须在读取 os.getenv 之前执行)
load_dotenv()


class HelloAgentsLLM:
    """
    LLM 客户端。
    用于调用任何兼容 OpenAI 接口的服务,默认使用流式响应。

    入参:
      model: 模型ID,缺省读 .env 的 LLM_MODEL_ID
      apiKey: API密钥,缺省读 .env 的 LLM_API_KEY
      baseUrl: 服务地址,缺省读 .env 的 LLM_BASE_URL
      timeout: 请求超时秒数,缺省读 .env 的 LLM_TIMEOUT(默认60)
      debug: 是否打印每个原始 chunk 的 JSON 数据包(教学调试用)
    """

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
        '''
        调用大语言模型进行思考,流式接收并返回其完整响应。

        入参: messages 消息列表; temperature 采样温度(0=最确定)
        返回: 完整回复字符串;调用失败返回 None
        '''
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
