"""测试讯飞星火 Embedding API 的多种认证方式。"""

from dotenv import load_dotenv
import os
import requests
import base64

load_dotenv()

ak = os.getenv("EMBED_API_KEY")
url = os.getenv("EMBED_BASE_URL", "").rstrip("/") + "/embeddings"
model = os.getenv("EMBED_MODEL_NAME")

parts = ak.split(":")
b64 = base64.b64encode(ak.encode()).decode()

print(f"API Key: {parts[0][:10]}...:{parts[1][:10]}...")
print(f"URL: {url}")
print(f"Model: {model}")
print()

# 方法1: Basic Auth (key:secret)
r1 = requests.post(url, auth=(parts[0], parts[1]), json={"model": model, "input": "你好"})
print(f"[Basic Auth] {r1.status_code}: {r1.text[:200]}")

# 方法2: Bearer 直接传完整 key
r2 = requests.post(url, headers={"Authorization": f"Bearer {ak}", "Content-Type": "application/json"}, json={"model": model, "input": "你好"})
print(f"[Bearer完整] {r2.status_code}: {r2.text[:200]}")

# 方法3: Bearer 只传前半部分
r3 = requests.post(url, headers={"Authorization": f"Bearer {parts[0]}", "Content-Type": "application/json"}, json={"model": model, "input": "你好"})
print(f"[Bearer前半] {r3.status_code}: {r3.text[:200]}")

# 方法4: Bearer base64(api_key:api_secret)
r4 = requests.post(url, headers={"Authorization": f"Bearer {b64}", "Content-Type": "application/json"}, json={"model": model, "input": "你好"})
print(f"[Bearer b64] {r4.status_code}: {r4.text[:200]}")

# 方法5: 参考讯飞其他API的鉴权方式 - 可能在 header 里传 api_key
r5 = requests.post(url, headers={"api_key": ak, "Content-Type": "application/json"}, json={"model": model, "input": "你好"})
print(f"[Header api_key] {r5.status_code}: {r5.text[:200]}")

# 方法6: 参考讯飞SPARK API用 Authorization: 格式 key:secret
r6 = requests.post(url, headers={"Authorization": ak, "Content-Type": "application/json"}, json={"model": model, "input": "你好"})
print(f"[Auth直接key:secret] {r6.status_code}: {r6.text[:200]}")