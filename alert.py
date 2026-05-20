"""
极端天气即时预警脚本
每 6 小时运行一次，只有发现极端/严重天气时才推送邮件
"""
import os
import sys
import io
import requests
from datetime import datetime, timezone, timedelta
from config import REGIONS, ALL_STATES, ALERT_CN, SEVERITY_CN, STATE_FULL_CN, STATE_CN, AREA_TERM_CN

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

session = requests.Session()
retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
session.mount("https://", HTTPAdapter(max_retries=retries))

ET = timezone(timedelta(hours=-5))

# 只关注严重和极端级别
CRITICAL_SEVERITIES = ["Extreme", "Severe"]


def translate_area(area_text):
    """将 NWS 区域描述翻译成中文"""
    import re
    if not area_text:
        return ""
    text = area_text
    # 替换多词术语（按长度降序，避免部分匹配）
    for en in sorted(AREA_TERM_CN, key=len, reverse=True):
        text = text.replace(en, AREA_TERM_CN[en])
    # 替换州全名（按长度降序）
    for en in sorted(STATE_FULL_CN, key=len, reverse=True):
        text = text.replace(en, STATE_FULL_CN[en])
    # 替换州代码（如 ", LA" → ", 路易斯安那州"）
    for code, cn in STATE_CN.items():
        text = re.sub(r',\s*' + code + r'\b', f', {cn}', text)
        text = re.sub(r'\b' + code + r'\b', cn, text)
    # 替换剩余常见词
    text = text.replace(" and ", "、").replace("; ", "；")
    # County → 县
    text = text.replace(" County", "县").replace(" county", "县")
    return text


def translate_headline(headline):
    """将 NWS 预警标题翻译成中文"""
    import re
    if not headline:
        return ""
    # NWS 标准格式: "{Event} issued {Month} {Day} at {Time} {TZ} until {Month} {Day} at {Time} {TZ} by NWS {Office}"
    # 或简短格式: "{Event} issued {Month} {Day} at {Time} {TZ} by NWS {Office}"
    m = re.match(r'(.+?) issued (.*?) by NWS (.+)', headline)
    if not m:
        return translate_area(headline)
    event_en = m.group(1).strip()
    time_part = m.group(2).strip()
    event_cn = ALERT_CN.get(event_en, event_en)
    # 解析时间: "May 19 at 10:03AM CDT until May 24 at 7:00AM CDT"
    until_m = re.match(r'(\w+ \d+) at (\S+) (\S+) until (\w+ \d+) at (\S+) (\S+)', time_part)
    if until_m:
        s_date, s_time, s_tz, e_date, e_time, e_tz = until_m.groups()
        return f"{event_cn}，{s_date} {s_time}({s_tz})发布，有效期至{e_date} {e_time}({e_tz})"
    # 无 until 的简短格式
    short_m = re.match(r'(\w+ \d+) at (\S+) (\S+)', time_part)
    if short_m:
        s_date, s_time, s_tz = short_m.groups()
        return f"{event_cn}，{s_date} {s_time}({s_tz})发布"
    return f"{event_cn}，{translate_area(time_part)}"


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
            lines.append(f"     类型: {a['event_cn']}（{a['event']}）")
            lines.append(f"     区域: {translate_area(a['area'])}")
            if a["headline"]:
                lines.append(f"     概要: {translate_headline(a['headline'])}")
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
        push_email(message, "！！美国极端天气预警！！")
    else:
        print("平安无事，不推送。")
