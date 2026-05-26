"""
美国和德国公假提醒
提前7天推送假日预告，帮助安排生产和商务活动
"""
import os
import sys
import io
from datetime import datetime, timezone, timedelta
import holidays

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ET = timezone(timedelta(hours=-5))
US_COUNTRY = "US"
DE_COUNTRY = "DE"

# 美国联邦假日（中英对照）
US_HOLIDAYS_CN = {
    "New Year's Day":        "元旦",
    "Martin Luther King Jr. Day": "马丁·路德·金纪念日",
    "Presidents' Day":       "总统日",
    "Memorial Day":          "阵亡将士纪念日",
    "Independence Day":      "独立日",
    "Labor Day":             "劳动节",
    "Columbus Day":          "哥伦布日",
    "Veterans Day":          "退伍军人节",
    "Thanksgiving Day":      "感恩节",
    "Christmas Day":         "圣诞节",
}

# 德国联邦假日（中英对照）- 全德统一假日
DE_HOLIDAYS_CN = {
    "Neujahrstag":               "元旦",
    "Karfreitag":                "圣周五（耶稣受难日）",
    "Ostersonntag":              "复活节",
    "Ostermontag":               "复活节次日",
    "Tag der Arbeit":            "劳动节",
    "Christi Himmelfahrt":      "耶稣升天节",
    "Pfingstsonntag":           "圣灵降临节",
    "Pfingstmontag":            "圣灵降临节次日",
    "Tag der Deutschen Einheit": "德国统一日",
    "Weihnachtstag":            "圣诞节",
    "Zweiter Weihnachtsfeiertag": "圣诞节次日",
}


def get_upcoming_holidays(country_code, year, days=14):
    """获取未来N天内即将到来的假日"""
    today = datetime.now(ET).date()
    start = today
    end = today + timedelta(days=days)

    if country_code == US_COUNTRY:
        holiday_map = US_HOLIDAYS_CN
        country_holidays = holidays.US(years=range(year - 1, year + 2))
    else:
        holiday_map = DE_HOLIDAYS_CN
        country_holidays = holidays.Germany(years=range(year - 1, year + 2))

    results = []
    for dt in (start + timedelta(n) for n in range((end - start).days + 1)):
        if dt in country_holidays:
            holiday_name = country_holidays[dt]
            cn_name = holiday_map.get(holiday_name, holiday_name)
            days_until = (dt - today).days
            results.append({
                "date": dt,
                "days_until": days_until,
                "en": holiday_name,
                "cn": cn_name,
                "weekday": weekday_cn(dt.weekday()),
            })
    return results


def weekday_cn(w):
    return ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][w]


def build_message(us_holidays, de_holidays):
    """构建假日提醒消息"""
    now = datetime.now(ET)
    today = now.date()
    lines = [
        f"📅 美德公假预告（7天内）",
        f"扫描日期: {today.strftime('%Y-%m-%d')} ({weekday_cn(today.weekday())})",
        "=" * 44,
        "",
    ]

    # 美国假日
    us_in_7 = [h for h in us_holidays if h["days_until"] <= 7]
    us_later = [h for h in us_holidays if 7 < h["days_until"] <= 14]

    if us_in_7:
        lines.append("🇺🇸 美国联邦假日（7天内）")
        lines.append("-" * 40)
        for h in us_in_7:
            days_str = "今天" if h["days_until"] == 0 else f"{h['days_until']}天后"
            lines.append(f"  • {h['date'].strftime('%m/%d')} {h['cn']}({h['en']}) — {days_str} {h['weekday']}")
        lines.append("")

    if us_later:
        lines.append("🇺🇸 美国联邦假日（8-14天内）")
        lines.append("-" * 40)
        for h in us_later:
            lines.append(f"  • {h['date'].strftime('%m/%d')} {h['cn']}({h['en']}) — {h['days_until']}天后 {h['weekday']}")
        lines.append("")

    if not us_in_7 and not us_later:
        lines.append("🇺🇸 美国：无7天内假日")
        lines.append("")

    # 德国假日
    de_in_7 = [h for h in de_holidays if h["days_until"] <= 7]
    de_later = [h for h in de_holidays if 7 < h["days_until"] <= 14]

    if de_in_7:
        lines.append("🇩🇪 德国联邦假日（全德统一，7天内）")
        lines.append("-" * 40)
        for h in de_in_7:
            days_str = "今天" if h["days_until"] == 0 else f"{h['days_until']}天后"
            lines.append(f"  • {h['date'].strftime('%m/%d')} {h['cn']}({h['en']}) — {days_str} {h['weekday']}")
        lines.append("")

    if de_later:
        lines.append("🇩🇪 德国联邦假日（8-14天内）")
        lines.append("-" * 40)
        for h in de_later:
            lines.append(f"  • {h['date'].strftime('%m/%d')} {h['cn']}({h['en']}) — {h['days_until']}天后 {h['weekday']}")
        lines.append("")

    if not de_in_7 and not de_later:
        lines.append("🇩🇪 德国：无7天内假日")
        lines.append("")

    lines.append("=" * 44)
    lines.append("💡 提示：假日期间美国/德国商务活动可能受影响，请提前安排生产和物流")
    return "\n".join(lines)


def push_email(message):
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
    msg["Subject"] = "📅 美德公假提醒"
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
    """企业微信 Webhook 推送"""
    webhook_url = os.environ.get("WECOM_WEBHOOK", "")
    if not webhook_url:
        return False
    try:
        resp = requests_post(webhook_url, json={"msgtype": "text", "text": {"content": message}}, timeout=30)
        result = resp.json()
        return result.get("errcode") == 0
    except Exception:
        return False


def push_feishu(message):
    """飞书 Webhook 推送"""
    webhook_url = os.environ.get("FEISHU_WEBHOOK", "")
    if not webhook_url:
        return False
    try:
        resp = requests_post(webhook_url, json={"msg_type": "text", "content": {"text": message}}, timeout=30)
        result = resp.json()
        return result.get("code") == 0
    except Exception:
        return False


def push_dingtalk(message):
    """钉钉 Webhook 推送"""
    webhook_url = os.environ.get("DINGTALK_WEBHOOK", "")
    if not webhook_url:
        return False
    try:
        resp = requests_post(webhook_url, json={"msgtype": "text", "text": {"content": message}}, timeout=30)
        result = resp.json()
        return result.get("errcode") == 0
    except Exception:
        return False


def push_pushplus(message):
    """PushPlus 推送到微信"""
    token = os.environ.get("PUSHPLUS_TOKEN", "")
    if not token:
        return False
    try:
        data = {
            "token": token,
            "title": "美德公假提醒",
            "content": f"<pre style='font-size:14px;line-height:1.6'>{message}</pre>",
            "template": "html",
        }
        resp = requests_post("http://www.pushplus.plus/send", json=data, timeout=30)
        result = resp.json()
        return result.get("code") == 200
    except Exception:
        return False


def push_toast(title, body):
    """Windows 原生 MessageBox 弹窗（兼容 Win10/Win11）"""
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(
            0,
            body,
            title,
            0x40 | 0x1  # MB_ICONINFORMATION | MB_OKCANCEL
        )
        print("弹窗推送: 成功")
        return True
    except Exception as e:
        print(f"弹窗推送: 失败 - {e}")
        return False


def requests_post(url, **kwargs):
    import requests
    return requests.post(url, **kwargs)


def push_all(message, us_holidays, de_holidays):
    """尝试所有已配置的推送方式"""
    us_in_7 = [h for h in us_holidays if h["days_until"] <= 7]
    de_in_7 = [h for h in de_holidays if h["days_until"] <= 7]

    results = []
    results.append(push_email(message))
    results.append(push_wecom(message))
    results.append(push_feishu(message))
    results.append(push_dingtalk(message))
    results.append(push_pushplus(message))

    # Toast：始终弹窗
    if us_in_7 or de_in_7:
        toast_lines = ["📅 公假提醒（7天内）"]
        if us_in_7:
            for h in us_in_7:
                toast_lines.append(f"🇺🇸 {h['cn']} {h['date'].strftime('%m/%d')} {h['weekday']}")
        if de_in_7:
            for h in de_in_7:
                toast_lines.append(f"🇩🇪 {h['cn']} {h['date'].strftime('%m/%d')} {h['weekday']}")
    else:
        # 7天内无假日，显示下一个假日
        us_next = us_holidays[0] if us_holidays else None
        de_next = de_holidays[0] if de_holidays else None
        toast_lines = ["📅 近期无假日，提前告知下一个："]
        if us_next:
            toast_lines.append(f"🇺🇸 {us_next['cn']} — {us_next['days_until']}天后 ({us_next['date'].strftime('%m/%d')} {us_next['weekday']})")
        if de_next:
            toast_lines.append(f"🇩🇪 {de_next['cn']} — {de_next['days_until']}天后 ({de_next['date'].strftime('%m/%d')} {de_next['weekday']})")

    toast_body = "\n".join(toast_lines)
    results.append(push_toast("美德公假提醒", toast_body))

    if not any(r for r in results if r):
        print("\n未配置任何推送方式，消息仅打印到控制台")


if __name__ == "__main__":
    today = datetime.now(ET).date()
    year = today.year

    print("正在查询美国和德国公假...")
    us_holidays = get_upcoming_holidays(US_COUNTRY, year, days=60)
    de_holidays = get_upcoming_holidays(DE_COUNTRY, year, days=60)

    print(f"美国假日（60天内）: {len(us_holidays)} 个")
    print(f"德国假日（60天内）: {len(de_holidays)} 个")

    message = build_message(us_holidays, de_holidays)
    print("\n" + message)

    print("\n--- 开始推送 ---")
    push_all(message, us_holidays, de_holidays)