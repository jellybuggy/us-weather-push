import os
import json
import smtplib
import time
import requests
from email.mime.text import MIMEText
from datetime import datetime, timezone, timedelta
from config import REGIONS, WEATHER_CN, FORECAST_DAYS, ALERT_CN, SEVERITY_CN

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

session = requests.Session()
retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
session.mount("https://", HTTPAdapter(max_retries=retries))

ET = timezone(timedelta(hours=-5))

WEEKDAY_CN = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
WEEKDAY_EN = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DAY_NAME_MAP = {
    "Today": "今天", "Tonight": "今晚",
    "Overnight": "今夜",
    "Memorial Day": "阵亡将士纪念日",
    "Independence Day": "独立日",
    "Labor Day": "劳动节",
    "Thanksgiving Day": "感恩节",
    "Christmas Day": "圣诞节",
    "New Year's Day": "元旦",
    "Martin Luther King Jr Day": "马丁路德金纪念日",
    "Presidents' Day": "总统日",
    "Veterans Day": "退伍军人节",
    "Columbus Day": "哥伦布日",
}


def translate_day(name):
    """把 Today/Wednesday/Wednesday Night 翻译成中文"""
    if name in DAY_NAME_MAP:
        return DAY_NAME_MAP[name]
    night = ""
    base = name
    if name.endswith(" Night"):
        night = "晚"
        base = name.replace(" Night", "")
    for en, cn in zip(WEEKDAY_EN, WEEKDAY_CN):
        if base == en:
            return cn + night
    return name


def translate_wind(wind_str):
    """把 '8 to 15 mph' 翻译成 '13~24 km/h 4~6级'"""
    if not wind_str:
        return ""
    import re
    nums = re.findall(r'\d+', wind_str)
    if not nums:
        return wind_str
    nums = [int(n) for n in nums]
    lo = min(nums)
    hi = max(nums)
    # mph → km/h (×1.609)
    km_lo = round(lo * 1.609)
    km_hi = round(hi * 1.609)
    # 蒲福风级对照
    def beaufort(kmh):
        if kmh < 2: return 0
        if kmh < 6: return 1
        if kmh < 12: return 2
        if kmh < 20: return 3
        if kmh < 29: return 4
        if kmh < 39: return 5
        if kmh < 50: return 6
        if kmh < 62: return 7
        if kmh < 75: return 8
        if kmh < 89: return 9
        if kmh < 103: return 10
        if kmh < 117: return 11
        return 12
    b_lo = beaufort(km_lo)
    b_hi = beaufort(km_hi)
    if b_lo == b_hi:
        return f"{km_lo}~{km_hi}km/h {b_lo}级"
    return f"{km_lo}~{km_hi}km/h {b_lo}~{b_hi}级"


def translate_weather(text):
    if not text:
        return "未知"
    for en, cn in WEATHER_CN.items():
        if en.lower() in text.lower():
            return cn
    return text


def celsius_from_f(f):
    if f is None:
        return "--"
    return round((f - 32) * 5 / 9)


def get_forecast(lat, lon):
    headers = {"User-Agent": "US-Weather-Push/1.0", "Accept": "application/geo+json"}
    points_url = f"https://api.weather.gov/points/{lat},{lon}"
    resp = session.get(points_url, headers=headers, timeout=30)
    if resp.status_code != 200:
        return None
    forecast_url = resp.json().get("properties", {}).get("forecast")
    if not forecast_url:
        return None
    resp = session.get(forecast_url, headers=headers, timeout=30)
    if resp.status_code != 200:
        return None
    periods = resp.json().get("properties", {}).get("periods", [])
    return periods[:FORECAST_DAYS * 2]


def get_alerts(state_code):
    headers = {"User-Agent": "US-Weather-Push/1.0", "Accept": "application/geo+json"}
    url = f"https://api.weather.gov/alerts?area={state_code}&status=actual"
    try:
        resp = session.get(url, headers=headers, timeout=30)
        if resp.status_code != 200:
            return []
        features = resp.json().get("features", [])
        alerts = []
        for f in features:
            props = f.get("properties", {})
            event = props.get("event", "")
            severity = props.get("severity", "")
            headline = props.get("headline", "")
            if event:
                event_cn = ALERT_CN.get(event, event)
                alerts.append({
                    "event": event,
                    "event_cn": event_cn,
                    "severity": severity,
                    "headline": headline,
                })
        return alerts
    except Exception:
        return []


def format_region_weather(region_name, region_data):
    lines = [f"\U0001F4CD {region_name}"]
    lines.append(f"   州: {', '.join(region_data['states'])}")
    lines.append("")
    for city in region_data["cities"]:
        periods = get_forecast(city["lat"], city["lon"])
        if not periods:
            lines.append(f"  {city['name']}({city['en']}): 数据获取失败")
            lines.append("")
            continue
        lines.append(f"  {city['name']}({city['en']})")
        for p in periods:
            name = p.get("name", "")
            temp_c = celsius_from_f(p.get("temperature"))
            desc = translate_weather(p.get("shortForecast", ""))
            wind = p.get("windSpeed", "")
            wind = translate_wind(p.get("windSpeed", ""))
            lines.append(f"    {translate_day(name)}: {desc} {temp_c}°C {wind}")
        lines.append("")
    # 扫描该区域所有州的预警
    all_region_alerts = []
    for st in region_data["states"]:
        st_alerts = get_alerts(st)
        for a in st_alerts:
            a["state"] = st
            all_region_alerts.append(a)

    # 去重 + 只显示中等以上
    seen = set()
    shown = []
    sev_order = {"Extreme": 0, "Severe": 1, "Moderate": 2, "Minor": 3, "Unknown": 4}
    for a in sorted(all_region_alerts, key=lambda x: sev_order.get(x["severity"], 4)):
        key = a["event"] + a["state"]
        if key not in seen and sev_order.get(a["severity"], 4) <= 2:
            seen.add(key)
            shown.append(a)

    if shown:
        lines.append(f"  == 天气预警 ==")
        for a in shown[:6]:
            sv_cn = SEVERITY_CN.get(a["severity"], a["severity"])
            marker = ">>>" if a["severity"] in ("Extreme", "Severe") else ">"
            lines.append(f"    {marker} [{sv_cn}] {a['event_cn']} ({a['state']})")
        lines.append("")
    return "\n".join(lines)


def build_message():
    now = datetime.now(ET)
    date_str = now.strftime("%Y-%m-%d")
    lines = [
        f"US Weather Forecast",
        f"Date: {date_str}  Days: {FORECAST_DAYS}",
        "=" * 40,
        "",
    ]
    for name, data in REGIONS.items():
        try:
            lines.append(format_region_weather(name, data))
        except Exception as e:
            lines.append(f"{name}: ERROR - {e}")
            lines.append("")
    lines.append("=" * 40)
    lines.append("Source: NWS (api.weather.gov)")
    return "\n".join(lines)


# ==================== 推送模块 ====================

def push_email(message):
    """邮件推送（完全免费，推荐 QQ邮箱/163邮箱）"""
    smtp_server = os.environ.get("EMAIL_SMTP", "")        # 如 smtp.qq.com
    smtp_port = int(os.environ.get("EMAIL_PORT", "465"))
    sender = os.environ.get("EMAIL_SENDER", "")            # 发件邮箱
    password = os.environ.get("EMAIL_PASSWORD", "")        # 授权码（不是登录密码）
    receiver = os.environ.get("EMAIL_RECEIVER", "")        # 收件邮箱

    if not all([smtp_server, sender, password, receiver]):
        print("邮件推送: 未配置完整，跳过")
        return False

  title = "今日美国各地天气"
    msg = MIMEText(message, "plain", "utf-8")
    msg["Subject"] = title
    msg["From"] = sender
    msg["To"] = receiver

    try:
        server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        server.login(sender, password)
        server.sendmail(sender, [receiver], msg.as_string())
        server.quit()
        print("邮件推送: 成功")
        return True
    except Exception as e:
        print(f"邮件推送: 失败 - {e}")
        return False


def push_wecom(message):
    """企业微信 Webhook 推送（完全免费，无限制）"""
    webhook_url = os.environ.get("WECOM_WEBHOOK", "")
    if not webhook_url:
        print("企业微信推送: 未配置 WECOM_WEBHOOK，跳过")
        return False

    try:
        data = {
            "msgtype": "text",
            "text": {"content": message},
        }
        resp = session.post(webhook_url, json=data, timeout=30)
        result = resp.json()
        if result.get("errcode") == 0:
            print("企业微信推送: 成功")
            return True
        else:
            print(f"企业微信推送: 失败 - {result}")
            return False
    except Exception as e:
        print(f"企业微信推送: 失败 - {e}")
        return False


def push_feishu(message):
    """飞书 Webhook 推送（完全免费，无限制）"""
    webhook_url = os.environ.get("FEISHU_WEBHOOK", "")
    if not webhook_url:
        print("飞书推送: 未配置 FEISHU_WEBHOOK，跳过")
        return False

    try:
        data = {
            "msg_type": "text",
            "content": {"text": message},
        }
        resp = session.post(webhook_url, json=data, timeout=30)
        result = resp.json()
        if result.get("code") == 0:
            print("飞书推送: 成功")
            return True
        else:
            print(f"飞书推送: 失败 - {result}")
            return False
    except Exception as e:
        print(f"飞书推送: 失败 - {e}")
        return False


def push_dingtalk(message):
    """钉钉 Webhook 推送（完全免费，无限制）"""
    webhook_url = os.environ.get("DINGTALK_WEBHOOK", "")
    if not webhook_url:
        print("钉钉推送: 未配置 DINGTALK_WEBHOOK，跳过")
        return False

    try:
        data = {
            "msgtype": "text",
            "text": {"content": message},
        }
        resp = session.post(webhook_url, json=data, timeout=30)
        result = resp.json()
        if result.get("errcode") == 0:
            print("钉钉推送: 成功")
            return True
        else:
            print(f"钉钉推送: 失败 - {result}")
            return False
    except Exception as e:
        print(f"钉钉推送: 失败 - {e}")
        return False


def push_pushplus(message):
    """PushPlus 推送到微信（免费版每天200条）"""
    token = os.environ.get("PUSHPLUS_TOKEN", "")
    if not token:
        print("PushPlus推送: 未配置 PUSHPLUS_TOKEN，跳过")
        return False

    try:
        data = {
            "token": token,
            "title": f"US Weather - {datetime.now(ET).strftime('%m/%d')}",
            "content": f"<pre style='font-size:14px;line-height:1.6'>{message}</pre>",
            "template": "html",
        }
        resp = session.post("http://www.pushplus.plus/send", json=data, timeout=30)
        result = resp.json()
        if result.get("code") == 200:
            print("PushPlus推送: 成功")
            return True
        else:
            print(f"PushPlus推送: 失败 - {result}")
            return False
    except Exception as e:
        print(f"PushPlus推送: 失败 - {e}")
        return False


def push_all(message):
    """尝试所有已配置的推送方式"""
    results = []
    results.append(push_email(message))
    results.append(push_wecom(message))
    results.append(push_feishu(message))
    results.append(push_dingtalk(message))
    results.append(push_pushplus(message))

    if not any(results):
        print("\n未配置任何推送方式，消息仅打印到控制台")


if __name__ == "__main__":
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print("正在获取美国各区域天气...")
    message = build_message()
    print(message)
    print("\n--- 开始推送 ---")
    push_all(message)
