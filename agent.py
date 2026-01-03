import requests

# 问答接口
response = requests.post("http://localhost:8000/ask", json={
    "question": "住宅建筑的防火间距是多少？",
    "session_id": "agent_001",
    "top_k": 5
})
result = response.json()
print(result["answer"])
print(result["references"])