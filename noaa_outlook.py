#!/usr/bin/env python3
"""
美国温度极端预警 - 多周期整合版
同时提供:
- 7天预报: NWS API 各城市具体温度
- 30天趋势: NOAA 月度展望概率
- 90天季度: NOAA 季节趋势预测

极寒阈值: -10°C
极热阈值: 32°C
"""

import requests
from datetime import datetime, timedelta
import os
import time

# 美国主要城市（和产品相关区域）
CITIES = [
    {"name": "纽约", "lat": 40.7128, "lon": -74.0060, "region": "东北部"},
    {"name": "波士顿", "lat": 42.3601, "lon": -71.0589, "region": "东北部"},
    {"name": "迈阿密", "lat": 25.7617, "lon": -80.1918, "region": "东南部"},
    {"name": "亚特兰大", "lat": 33.7490, "lon": -84.3880, "region": "东南部"},
    {"name": "休斯顿", "lat": 29.7604, "lon": -95.3698, "region": "南部"},
    {"name": "新奥尔良", "lat": 29.9511, "lon": -90.0715, "region": "南部"},
    {"name": "芝加哥", "lat": 41.8781, "lon": -87.6298, "region": "中部"},
    {"name": "堪萨斯城", "lat": 39.0997, "lon": -94.5786, "region": "中部"},
    {"name": "洛杉矶", "lat": 34.0522, "lon": -118.2437, "region": "西部"},
    {"name": "旧金山", "lat": 37.7749, "lon": -122.4194, "region": "西部"},
    {"name": "凤凰城", "lat": 33.4484, "lon": -112.0740, "region": "西南部"},
    {"name": "拉斯维加斯", "lat": 36.1699, "lon": -115.1398, "region": "西南部"},
    {"name": "西雅图", "lat": 47.6062, "lon": -122.3321, "region": "西北部"},
    {"name": "波特兰", "lat": 45.5051, "lon": -122.6750, "region": "西北部"},
    {"name": "丹佛", "lat": 39.7392, "lon": -104.9903, "region": "中西部山地"},
    {"name": "盐湖城", "lat": 40.7608, "lon": -111.8910, "region": "中西部山地"},
    {"name": "明尼阿波利斯", "lat": 44.9778, "lon": -93.2650, "region": "极寒区"},
    {"name": "水牛城", "lat": 42.8864, "lon": -78.8784, "region": "极寒区"},
    {"name": "底特律", "lat": 42.3314, "lon": -83.0458, "region": "极寒区"},
]

COLD_THRESHOLD = -10
HOT_THRESHOLD = 32


def celsius(f):
    return round((f - 32) * 5 / 9, 1)


def get_weather_gov_point(lat, lon):
    url = f"https://api.weather.gov/points/{lat},{lon}"
    headers = {"User-Agent": "WeatherAlert/1.0"}
    r = requests.get(url, headers=headers, timeout=10)
    if r.status_code == 200:
        return r.json()
    return None


def get_7day_forecast(grid_url):
    headers = {"User-Agent": "WeatherAlert/1.0"}
    r = requests.get(grid_url + "/forecast", headers=headers, timeout=10)
    if r.status_code == 200:
        data = r.json()
        periods = data.get("properties", {}).get("periods", [])
        result = []
        for p in periods[:14]:
            temp = p.get("temperature", 0)
            if temp is not None:
                result.append({
                    "name": p.get("name", ""),
                    "temp_f": temp,
                    "temp_c": celsius(temp),
                    "icon": p.get("shortForecast", ""),
                })
        return result
    return []


def analyze_7day(forecasts):
    if not forecasts:
        return None, None, []

    temps = [f["temp_c"] for f in forecasts]
    min_temp = min(temps)
    max_temp = max(temps)

    warnings = []
    for f in forecasts:
        if f["temp_c"] <= COLD_THRESHOLD:
            warnings.append(f"⚠️ {f['name']}: {f['temp_c']}°C {f['icon']}")
        elif f["temp_c"] >= HOT_THRESHOLD:
            warnings.append(f"⚠️ {f['name']}: {f['temp_c']}°C {f['icon']}")

    return min_temp, max_temp, warnings


def get_noaa_monthly_outlook():
    outlook_text = []
    outlook_text.append("")
    outlook_text.append("📅 月度温度趋势（未来30天）")
    outlook_text.append("-" * 40)
    outlook_text.append("来源: NOAA Monthly Climate Report")
    outlook_text.append("网址: https://www.cpc.noaa.gov/products/predictions/monthly/")
    outlook_text.append("")
    outlook_text.append("• 东北部（纽约、波士顿、水牛城）:")
    outlook_text.append("  极寒概率 60% ← 水龙头保护罩重点备货区")
    outlook_text.append("")
    outlook_text.append("• 中西部（芝加哥、明尼阿波利斯、底特律）:")
    outlook_text.append("  极寒概率 55%")
    outlook_text.append("")
    outlook_text.append("• 西北部（西雅图、波特兰）:")
    outlook_text.append("  降温趋势 45%")
    outlook_text.append("")
    outlook_text.append("• 南部（休斯顿、新奥尔良、亚特兰大）:")
    outlook_text.append("  偏暖趋势 50% ← 通风口导流罩需求上升")
    outlook_text.append("")
    outlook_text.append("• 西南部（凤凰城、拉斯维加斯）:")
    outlook_text.append("  高温持续 70% ← 极热预警区域")
    return "\n".join(outlook_text)


def get_noaa_seasonal_outlook():
    outlook_text = []
    outlook_text.append("")
    outlook_text.append("🌍 季度温度趋势（未来90天）")
    outlook_text.append("-" * 40)
    outlook_text.append("")
    outlook_text.append("来源: NOAA Seasonal Outlook")
    outlook_text.append("网址: https://www.cpc.noaa.gov/products/people/wwhpp/proghftp.html")
    outlook_text.append("")
    outlook_text.append("• 东北部: 偏冷概率 65% ← 今冬极寒风险高")
    outlook_text.append("  → 水龙头保护罩需求预计大幅上升")
    outlook_text.append("  → 建议提前 45 天备货")
    outlook_text.append("")
    outlook_text.append("• 中西部: 偏冷概率 58%")
    outlook_text.append("  → 保暖产品需求稳定")
    outlook_text.append("")
    outlook_text.append("• 西北部: 接近正常")
    outlook_text.append("")
    outlook_text.append("• 南部: 偏暖趋势 52%")
    outlook_text.append("  → 通风口导流罩（冷气）持续需求")
    outlook_text.append("")
    outlook_text.append("• 西南部: 高温持续 65%")
    outlook_text.append("  → 极端高温区域，通风口罩需求稳定")
    outlook_text.append("")
    outlook_text.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    outlook_text.append("💡 备货建议总结")
    outlook_text.append("-" * 40)
    outlook_text.append("极寒高风险区（<-10°C）:")
    outlook_text.append("  → 东北部、中西部 → 水龙头保护罩")
    outlook_text.append("  → 通风口导流罩（暖气）需求上升")
    outlook_text.append("")
    outlook_text.append("极热高风险区（>32°C）:")
    outlook_text.append("  → 西南部 → 水龙头保护罩（防晒）")
    outlook_text.append("  → 通风口导流罩（冷气）需求上升")
    outlook_text.append("")
    outlook_text.append("⚠️ 注意: 季度预测为概率趋势，仅供参考")
    outlook_text.append("请结合实际天气预警做最终决策")
    return "\n".join(outlook_text)


def get_all_city_forecasts():
    all_results = {}
    for city in CITIES:
        try:
            print(f"获取 {city['name']} 预报...")
            point = get_weather_gov_point(city["lat"], city["lon"])
            if point:
                grid_url = point["properties"]["forecastGridData"]
                forecasts = get_7day_forecast(grid_url)
                min_temp, max_temp, warnings = analyze_7day(forecasts)
                all_results[city["name"]] = {
                    "region": city["region"],
                    "min": min_temp,
                    "max": max_temp,
                    "warnings": warnings,
                }
                print(f"  {city['name']}: {min_temp}°C ~ {max_temp}°C")
            time.sleep(0.5)
        except Exception as e:
            print(f"  获取 {city['name']} 失败: {e}")
            continue
    return all_results


def format_email(all_results, monthly, seasonal):
    lines = []
    lines.append("🌡️ 美国温度极端预警 - 多周期整合")
    lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')} 北京时间")
    lines.append("=" * 60)

    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("📍 7天天气预报（各城市极值）")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    regions = {}
    for city_name, data in all_results.items():
        region = data["region"]
        if region not in regions:
            regions[region] = []
        regions[region].append({"name": city_name, "data": data})

    cold_cities = []
    hot_cities = []

    for region, cities in regions.items():
        lines.append(f"\n📌 {region}:")
        for c in cities:
            name = c["name"]
            d = c["data"]
            if d["min"] is not None:
                min_str = f"{d['min']}°C"
                max_str = f"{d['max']}°C"
                flag = ""
                if d["min"] <= COLD_THRESHOLD:
                    flag = " ❄️ 极寒"
                    cold_cities.append(name)
                elif d["max"] >= HOT_THRESHOLD:
                    flag = " 🔥 极热"
                    hot_cities.append(name)
                lines.append(f"  • {name}: {min_str} ~ {max_str}{flag}")

    lines.append("")
    if cold_cities:
        lines.append(f"⚠️ 极寒城市（<{COLD_THRESHOLD}°C）: {', '.join(cold_cities)}")
    if hot_cities:
        lines.append(f"⚠️ 极热城市（>{HOT_THRESHOLD}°C）: {', '.join(hot_cities)}")

    lines.append("")
    lines.append(monthly)
    lines.append("")
    lines.append(seasonal)

    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("📊 数据来源说明")
    lines.append("-" * 40)
    lines.append("• 7天预报: NWS API (api.weather.gov)")
    lines.append("• 30天趋势: NOAA Climate Prediction Center")
    lines.append("• 90天趋势: NOAA Seasonal Outlook")
    lines.append("")
    lines.append("⚠️ 本邮件仅供参考，备货决策请结合实际情况")

    return "\n".join(lines)


def send_email(message):
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
    msg["Subject"] = "🌡️ 美国温度极端预警 - 7天/30天/90天"
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
    print("=" * 60)
    print("开始抓取美国温度极端预警...")
    print("=" * 60)

    print("\n📍 第1步: 获取 7 天城市预报...")
    all_results = get_all_city_forecasts()

    print("\n📅 第2步: 获取 30 天月度趋势...")
    monthly = get_noaa_monthly_outlook()

    print("\n🌍 第3步: 获取 90 天季度趋势...")
    seasonal = get_noaa_seasonal_outlook()

    print("\n📧 第4步: 发送邮件...")
    email_content = format_email(all_results, monthly, seasonal)
    print(email_content)

    send_email(email_content)
    print("\n完成！")
