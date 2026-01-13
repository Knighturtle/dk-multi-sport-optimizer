# src/notify.py
import os, json, time, requests
from dotenv import load_dotenv

load_dotenv()
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
SLACK_CHANNEL = os.getenv("SLACK_CHANNEL", "#dfs-logs")

def _truncate(s: str, n: int = 3500) -> str:
    return s if len(s) <= n else s[:n-3] + "..."

def send_slack(text: str, *, title: str | None = None):
    if not SLACK_WEBHOOK_URL:
        return False
    payload = {
        "channel": SLACK_CHANNEL,
        "username": "DFS Bot",
        "icon_emoji": ":bar_chart:",
        "text": f"*{title}*\n{text}" if title else text,
    }
    r = requests.post(SLACK_WEBHOOK_URL, data=json.dumps(payload), timeout=10)
    return r.ok

def send_discord(text: str, *, title: str | None = None):
    if not DISCORD_WEBHOOK_URL:
        return False
    content = f"**{title}**\n{text}" if title else text
    payload = {"content": _truncate(content)}
    r = requests.post(DISCORD_WEBHOOK_URL, data=payload, timeout=10)
    return r.ok

def notify_success(sport: str, n_lineups: int, output_path: str, extras: dict | None = None):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    extra_lines = ""
    if extras:
        for k, v in extras.items():
            extra_lines += f"\n{k}: {v}"
    body = (
        f"✅ ラインナップ生成 成功\n"
        f"日時: {ts}\n"
        f"スポーツ: {sport}\n"
        f"本数: {n_lineups}\n"
        f"出力: {output_path}{extra_lines}"
    )
    send_slack(body, title="DFS 完了")
    send_discord(f"✅ {sport} 成功 ({n_lineups}本)\n出力: {output_path}")

def notify_failure(reason: str, *, input_path: str | None = None):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    body = f"❌ 失敗\n日時: {ts}\n理由: {reason}"
    if input_path:
        body += f"\n入力: {input_path}"
    send_slack(body, title="DFS 失敗")
    send_discord(f"❌ 失敗: {reason}")
