"""
极端天气即时预警脚本
每 6 小时运行一次，只有发现极端/严重天气时才推送邮件
"""
import os
import sys
import io
import requests
from datetime import datetime, timezone, timedelta
from config import REGIONS, ALL_STATES, ALERT_CN, SEVERITY_CN

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

session = requests.Session()
retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
session.mount("https://", HTTPAdapter(max_retries=retries))

ET = timezone(timedelta(hours=-5))

# 只关注严重和极端级别
CRITICAL_SEVERITIES = ["Extreme", "Severe"]


def get_all_alerts():
    """获取所有州的活跃预警，按严重等级分类"""
    headers = {"User-Agent": "US-Weather-Push/1.0", "Accept": "application/geo+json"}
    all_alerts = []
    now = datetime.now(timezone.utc)

    for state in ALL_STATES:
        try:
            url = f"https://api.weather.gov/alerts?area={state}&status=actual"
            resp = session.get(url, headers=headers, timeout=30)
            if resp.status_code != 200:
                continue
            data = resp.json()
            if not data or "features" not in data:
                continue
            features = data.get("features", [])
            for f in features:
                props = f.get("properties") or {}
                severity = props.get("severity", "")
                event = props.get("event", "")
                area = props.get("areaDesc", "")
                headline = props.get("headline", "")
                description = props.get("description", "")
                expires_str = props.get("expires", "")

                # 过滤已过期的预警
                if expires_str:
                    try:
                        expires_dt = datetime.fromisoformat(expires_str.replace("Z", "+00:00"))
                        if expires_dt < now:
                            continue
                    except Exception:
                        pass

                if not event:
                    continue

                # 翻译
                event_cn = ALERT_CN.get(event, event)
                severity_cn = SEVERITY_CN.get(severity, severity)

                all_alerts.append({
                    "state": state,
                    "event": event,
                    "event_cn": event_cn,
                    "severity": severity,
                    "severity_cn": severity_cn,
                    "area": area,
                    "headline": headline,
                    "description": description[:200],
                    "expires": expires_str[:16] if expires_str else "",
                })
        except Exception as e:
            print(f"  {state}: 获取失败 - {e}")
            continue

    return all_alerts


def build_alert_message(alerts):
    """构建极端天气预警消息"""
    now = datetime.now(ET)
    date_str = now.strftime("%Y-%m-%d %H:%M 美东时间")

    # 筛选严重和极端
    critical = [a for a in alerts if a["severity"] in CRITICAL_SEVERITIES]

    if not critical:
        print(f"当前无极端/严重天气预警，不推送。共扫描 {len(ALL_STATES)} 个州。")
        return None

    lines = [
        f"!!! 美国极端天气预警 !!!",
        f"扫描时间: {date_str}",
        f"发现 {len(critical)} 条严重/极端预警",
        "=" * 50,
        "",
    ]

    # 按区域分组
    for region_name, region_data in REGIONS.items():
        region_states = region_data["states"]
        region_alerts = [a for a in critical if a["state"] in region_states]
        if not region_alerts:
            continue

        lines.append(f"[{region_name}] {', '.join(region_states)}")
        lines.append("")

        for a in region_alerts:
            marker = "!!!" if a["severity"] == "Extreme" else "!!"
            lines.append(f"  {marker} [{a['severity_cn']}] {a['event_cn']}")
            lines.append(f"     原文: {a['event']}")
            lines.append(f"     区域: {a['area']}")
            if a["headline"]:
                lines.append(f"     概要: {a['headline']}")
            if a["expires"]:
                lines.append(f"     到期: {a['expires']}")
            lines.append("")

    lines.append("=" * 50)
    lines.append("数据来源: NWS (api.weather.gov)")
    lines.append(f"下次扫描: 6小时后")

    return "\n".join(lines)


def push_email(message, subject):
    """邮件推送"""
    import smtplib
    from email.mime.text import MIMEText

    smtp_server = os.environ.get("EMAIL_SMTP", "")
    smtp_port = int(os.environ.get("EMAIL_PORT", "465"))
    sender = os.environ.get("EMAIL_SENDER", "")
    password = os.environ.get("EMAIL_PASSWORD", "")
    receiver = os.environ.get("EMAIL_RECEIVER", "")

    if not all([smtp_server, sender, password, receiver]):
        print("邮件推送: 未配置，跳过")
        return False

    msg = MIMEText(message, "plain", "utf-8")
    msg["Subject"] = subject
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


if __name__ == "__main__":
    print(f"扫描美国 {len(ALL_STATES)} 个州的极端天气预警...")
    alerts = get_all_alerts()
    print(f"共获取 {len(alerts)} 条预警")

    message = build_alert_message(alerts)
    if message:
        print(message)
        date_str = datetime.now(ET).strftime("%m/%d %H:%M")
        push_email(message, f"!!! 极端天气预警 - {date_str}")
    else:
        print("平安无事，不推送。")
