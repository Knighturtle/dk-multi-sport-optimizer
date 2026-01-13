import os, json, requests
from dotenv import load_dotenv

load_dotenv()  # .env を読み込む

url = os.getenv("SLACK_WEBHOOK_URL")
channel = os.getenv("SLACK_CHANNEL", "#dfs-logs")

payload = {
    "channel": channel,
    "text": "✅ Slack接続テスト (Pythonから送信)",
    "username": "DFS Bot",
    "icon_emoji": ":bar_chart:"
}

res = requests.post(url, data=json.dumps(payload), timeout=10)
print("Status:", res.status_code, res.text)
