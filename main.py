import os
import requests

# 从环境变量中读取加密信息
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# 要追踪的单号列表（支持同时监控多个包裹）
TRACKING_NUMBERS = [
    "MY260268178425D",
    # "",
]

CACHE_FILE = "last_status.txt"


def load_cached_status():
    """读取上一次记录的状态"""
    if not os.path.exists(CACHE_FILE):
        return {}
    cached = {}
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("||")
            if len(parts) == 2:
                cached[parts[0]] = parts[1]
    return cached


def save_cached_status(status_dict):
    """保存最新状态到本地缓存文件"""
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        for tracking_num, status_id in status_dict.items():
            f.write(f"{tracking_num}||{status_id}\n")


def send_telegram_msg(message):
    """发送消息给 Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram 发送异常: {e}")


def check_spx_status():
    cached_status = load_cached_status()
    updated_status = cached_status.copy()

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://spx.com.my/",
    }

    for tracking_num in TRACKING_NUMBERS:
        url = f"https://spx.com.my/api/v2/fleet_order/tracking/search?sls_tracking_number={tracking_num}"
        try:
            res = requests.get(url, headers=headers, timeout=10)
            data = res.json()

            if data.get("retcode") == 0 and "data" in data:
                tracks = data["data"].get("tracks", [])
                if tracks:
                    latest = tracks[0]
                    status_time = latest.get("ctime_str", "")
                    status_desc = latest.get("description", "")
                    current_id = f"{status_time}_{status_desc}"

                    last_id = cached_status.get(tracking_num)

                    # 1. 首次加入监控
                    if last_id is None:
                        updated_status[tracking_num] = current_id
                        msg = f"📦 *SPX 追踪已初始化*\n单号: `{tracking_num}`\n当前状态: {status_desc}\n时间: {status_time}"
                        print(msg)
                        send_telegram_msg(msg)

                    # 2. 状态发生更新
                    elif current_id != last_id:
                        updated_status[tracking_num] = current_id
                        msg = (
                            f"🚨 *SPX 物流状态更新！*\n\n"
                            f"📦 *单号*: `{tracking_num}`\n"
                            f"📌 *最新进度*: {status_desc}\n"
                            f"🕒 *更新时间*: {status_time}"
                        )
                        print(msg)
                        send_telegram_msg(msg)
                    else:
                        print(f"单号 {tracking_num} 暂无更新。")
        except Exception as e:
            print(f"查询单号 {tracking_num} 异常: {e}")

    # 更新缓存记录
    save_cached_status(updated_status)


if __name__ == "__main__":
    check_spx_status()
