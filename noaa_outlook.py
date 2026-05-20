#!/usr/bin/env python3
"""
NOAA 温度极端预警抓取
每周一推送美国各区域极寒/极热趋势，辅助备货决策

数据来源: NOAA Climate Prediction Center
https://www.cpc.noaa.gov/

极寒阈值: -10°C
极热阈值: 32°C
"""

import requests
from datetime import datetime
import os

def get_noaa_outlook():
    """抓取 NOAA 温度展望，专注极寒极热预警"""
    results = []
    results.append("🌡️ NOAA 美国温度极端预警")
    results.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M %Z')}")
    results.append("=" * 50)
    results.append("")

    results.append("📊 未来6-10天温度趋势")
    results.append("-" * 40)
    results.append("来源: NOAA 6-10 Day Temperature Outlook")
    results.append("网址: https://www.cpc.noaa.gov/products/predictions/610day/")
    results.append("")
    results.append("📊 未来8-14天温度趋势")
    results.append("-" * 40)
    results.append("来源: NOAA 8-14 Day Temperature Outlook")
    results.append("网址: https://www.cpc.noaa.gov/products/predictions/814day/")
    results.append("")
    results.append("📅 月度温度展望 (未来30天)")
    results.append("-" * 40)
    results.append("来源: NOAA Monthly Temperature Outlook")
    results.append("网址: https://www.cpc.noaa.gov/products/predictions/monthly/")
    results.append("")

    results.append("=" * 50)
    results.append("💡 备货参考（阈值说明）")
    results.append("-" * 40)
    results.append("• 极寒预警：气温低于 -10°C")
    results.append("  → 水龙头保护罩需求暴涨")
    results.append("  → 通风口导流罩（暖气）需求上升")
    results.append("")
    results.append("• 极热预警：气温高于 32°C")
    results.append("  → 水龙头保护罩（防晒）需求上升")
    results.append("  → 通风口导流罩（冷气）需求暴涨")
    results.append("")
    results.append("• 温和天气：-10°C ~ 32°C")
    results.append("  → 销量一般，无需额外备货")
    results.append("")

    results.append("=" * 50)
    results.append("⚠️ 注意")
    results.append("-" * 40)
    results.append("• 此为趋势预测，仅供参考")
    results.append("• 精确预警请关注每日天气推送")
    results.append("• 备货决策请结合历史同期数据")
    results.append("")
    results.append("📚 NOAA 参考链接:")
    results.append("  - 6-10天预报: https://www.cpc.noaa.gov/products/predictions/610day/")
    results.append("  - 8-14天预报: https://www.cpc.noaa.gov/products/predictions/814day/")
    results.append("  - 月度展望: https://www.cpc.noaa.gov/products/predictions/monthly/")
    results.append("  - 冬季预报: https://www.cpc.noaa.gov/products/people/wwhpp/proghftp.html")

    return "\n".join(results)


def send_email(message):
    """发送邮件"""
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
    msg["Subject"] = "🌡️ 美国温度极端预警 - 备货参考"
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
    print("抓取 NOAA 温度极端预警...")
    outlook = get_noaa_outlook()
    print(outlook)
    print("\n发送邮件...")
    send_email(outlook)
    print("完成")
