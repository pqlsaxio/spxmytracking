import os
import requests

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# ⚠️ 请确保换成你的真实 SPX 运单号！
TRACKING_NUMBERS = [
    "MY260268178425D", # 改成你的真实单号
]

CACHE_FILE = "last_status.txt"

def load_cached_status():
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
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        for tracking_num, status_id in status_dict.items():
            f.write(f"{tracking_num}||{status_id}\n")

def send_telegram_msg(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ 未配置 Telegram Token 或 Chat ID，跳过发送消息")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        res = requests.post(url, json=payload, timeout=10)
        print(f"Telegram 推送结果: {res.status_code}")
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
        print(f"\n🔍 正在查询单号: {tracking_num} ...")
        url = f"https://spx.com.my/api/v2/fleet_order/tracking/search?sls_tracking_number={tracking_num}"
        try:
            res = requests.get(url, headers=headers, timeout=10)
            data = res.json()
            
            # 输出返回信息以供调试
            if data.get("retcode") != 0:
                print(f"❌ 接口返回异常: {data}")
                continue

            tracks = data.get("data", {}).get("tracks", [])
            if not tracks:
                print(f"⚠️ 未找到单号 {tracking_num} 的物流轨迹，请确认单号正确且已投递。")
                continue

            latest = tracks[0]
            status_time = latest.get("ctime_str", "")
            status_desc = latest.get("description", "")
            current_id = f"{status_time}_{status_desc}"
            
            print(f"✅ 查询成功！最新状态: [{status_time}] {status_desc}")

            last_id = cached_status.get(tracking_num)

            # 首次记录
            if last_id is None:
                updated_status[tracking_num] = current_id
                msg = f"📦 *SPX 追踪已初始化*\n单号: `{tracking_num}`\n当前状态: {status_desc}\n时间: {status_time}"
                send_telegram_msg(msg)

            # 状态有更新
            elif current_id != last_id:
                updated_status[tracking_num] = current_id
                msg = (
                    f"🚨 *SPX 物流状态更新！*\n\n"
                    f"📦 *单号*: `{tracking_num}`\n"
                    f"📌 *最新进度*: {status_desc}\n"
                    f"🕒 *更新时间*: {status_time}"
                )
                send_telegram_msg(msg)
            else:
                print(f"ℹ️ 单号 {tracking_num} 状态未发生变化。")

        except Exception as e:
            print(f"❌ 查询单号 {tracking_num} 出现异常: {e}")

    save_cached_status(updated_status)
    print(f"\n💾 写入缓存完成，当前缓存数据: {updated_status}")

if __name__ == "__main__":
    check_spx_status()
