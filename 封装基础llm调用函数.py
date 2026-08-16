import os
from openai import OpenAI
from dotenv import load_dotenv  #加载环境变量
# from typing import List,Dict,Any    #大写时即List要导入，小写时 python 3.9+ 版本后的可不用导入

'''
流程图
1. 加载环境变量
2. 初始化OpenAI客户端(传参，抛出ValueError异常，实例化)
3. 调用LLM API（response传参，流式响应返回for chunk in )
4. 客户端的使用并返回结果

涉及的未知python语法函数
os.getenv(key,默认值)
分隔字符串.join(可迭代对象) 作用：用【分隔字符串】把可迭代对象里面所有元素拼接成一条新字符串


其他知识点：
带上self的表示当前实例对象（比如a = CLclient()),不带self的是局部变量
'''

#先加载环境变量
load_dotenv()

#创建OpenAI客户端
class CLclient:
    '''
    LLM客户端
    用于调用任何兼容OpenAI接口的服务，并默认使用流式相应
    '''
    #参数名后面接的model: str = None表示参数model是一个字符串类型，默认值为None，保证调用时程序不会报错
    #timeout表示请求响应超时等待秒数默认为60，否则抛出异常（第三方SDK自动抛出）
    def __init__(self, api_key:str = None, model: str = None,base_url: str = None,timeout:int = None):
        '''
        初始化客户端，优先使用传入参数，如果未提供则使用.env的环境变量
        '''
        self.model = model or os.getenv("LLM_MODEL_ID")
        apikey = api_key or os.getenv("LLM_API_KEY")
        base_url = base_url or os.getenv("LLM_BASE_URL")
        #返回的是字符串，需要int来转换
        timeout = timeout or int(os.getenv("LLM_TIMEOUT",60))

        if not all([self.model,apikey,base_url]):   #校验兜底后的apikey,而不是入参api_key(入参为None时用.env兜底)
            raise ValueError("模型ID，API密钥和服务地址必须被提供或在.env文件中定义。")     #抛给上层调用函数

        #把上面构造的参数实例化
        self.client = OpenAI(api_key = apikey,base_url =base_url,timeout = timeout)

    def think(self,messages:list[dict[str,str]],temperature: float = 0) ->str :
        '''
        调用大语言模型思考，并返回其响应
        '''
        print(f"正在调用{self.model}模型...")
        try:
            response = self.client.chat.completions.create(
                model = self.model,
                messages = messages,
                temperature = temperature,
                stream = True,  #这里加不加逗号都不违法
            )

            #处理流式相应
            '''
            {"choices":[{"index":0,"message":{"role":"assistant","content":"文本内容"},"finish_reason":"stop"}]}
            {"choices":[{"index":0,"delta":{"content":"文本片段"},"finish_reason":null}]}
            '''
            print("已经成功建立流式连接，开始接收输出...")
            collected_content = []
            for chunk in response:
                if not chunk.choices:   #防止choices[0]时返回的是空数据包导致报错
                    continue
                content = chunk.choices[0].delta.content or ""
                print(content, end = "",flush = True)
                collected_content.append(content)
            print()     #流式输出后换行
            return "".join(collected_content)   #把['1','2','3']变成“123"
        except Exception as e:
            print(f"调用LLM API时发生错误:{e}")
            return None

# --- 客户端使用示例 ---
if __name__ == "__main__":
    try:
        llmclient = CLclient()

        mymessages = [
            {"role":"system","content":"你是一个智能助手帮我解决问题"},
            {"role":"user","content":"帮我写一个冒泡排序"}
        ]

        print("--- 正在调用LLM ---")
        responsetext = llmclient.think(mymessages)
        if responsetext:
            print("\n\n--- 完整的模型响应 ---")
            print(responsetext)
        else:
            print("--- 模型未返回有效内容 ---")
    except ValueError as e:
        print(e)


'''
报错:IndentationError: expected an indented block after function definition on line 48  
记得缩进
'''