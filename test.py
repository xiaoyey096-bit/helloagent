"""测试讯飞星火 Embedding API 是否连通。（直接 HTTP 请求，不受 SDK 路径拼接影响）"""

import requests
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("EMBED_API_KEY")
model = os.getenv("EMBED_MODEL_NAME")
base_url = os.getenv("EMBED_BASE_URL")

# 确保 base_url 不以 /embeddings 结尾，SDK 会自动拼接
# 但这里我们直接用 requests 手动拼接，确保路径正确
url = base_url.rstrip("/")
if not url.endswith("/embeddings"):
    url += "/embeddings"

print(f"请求URL: {url}")
print(f"模型: {model}")
print(f"API Key: {api_key[:20]}...")

resp = requests.post(
    url,
    headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    },
    json={"model": model, "input": "你好，世界，请把我转换成向量"}
)

print(f"\n状态码: {resp.status_code}")
print(f"响应: {resp.text[:500]}")

if resp.status_code == 200:
    data = resp.json()
    print(f"\n向量维度: {len(data['data'][0]['embedding'])}")
    print(f"前5个值: {data['data'][0]['embedding'][:5]}")
    print("✅ 连接成功！")