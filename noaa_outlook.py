#!/usr/bin/env python3
"""
50-Day Winter Replenishment Alert System

Module 2: 50-Day Winter Replenishment Alert
用于户外水龙头保暖罩的补货决策。

目标：
基于官方中长期趋势、NWS短期预警、CPC outlook、新闻和市场信号，
提前50天判断是否需要生产、发货、补FBA和调整Amazon广告。

硬性规则：
- 不允许编造30天、50天、90天具体温度
- 不允许编造极寒概率
- CPC长期数据只能表达 below normal / near normal / above normal 趋势
- 新闻/RSS只能作为 media signal / market signal，不能作为官方预警
- 每个结论必须注明来源
- 没有可靠数据时写"暂无可靠数据"
"""

import requests
from datetime import datetime, timedelta
import os
import time
import re

# ==================== 常量 ====================
SYSTEM_NAME = "50-Day Winter Replenishment Alert System"

# 极寒/极热阈值（摄氏）
COLD_THRESHOLD_C = -10
HOT_THRESHOLD_C = 32

# 华氏阈值
COLD_THRESHOLD_F = 14  # 14°F = -10°C
HOT_THRESHOLD_F = 90   # 90°F = 32°C

# 美国重点城市（覆盖主要销售区域）
CITIES = [
    {"name": "纽约", "lat": 40.7128, "lon": -74.0060, "state": "NY", "region": "Northeast"},
    {"name": "波士顿", "lat": 42.3601, "lon": -71.0589, "state": "MA", "region": "Northeast"},
    {"name": "水牛城", "lat": 42.8864, "lon": -78.8784, "state": "NY", "region": "Northeast"},
    {"name": "费城", "lat": 39.9526, "lon": -75.1652, "state": "PA", "region": "Northeast"},
    {"name": "芝加哥", "lat": 41.8781, "lon": -87.6298, "state": "IL", "region": "Midwest"},
    {"name": "底特律", "lat": 42.3314, "lon": -83.0458, "state": "MI", "region": "Midwest"},
    {"name": "明尼阿波利斯", "lat": 44.9778, "lon": -93.2650, "state": "MN", "region": "Midwest"},
    {"name": "丹佛", "lat": 39.7392, "lon": -104.9903, "state": "CO", "region": "Mountain"},
    {"name": "盐湖城", "lat": 40.7608, "lon": -111.8910, "state": "UT", "region": "Mountain"},
    {"name": "西雅图", "lat": 47.6062, "lon": -122.3321, "state": "WA", "region": "Northwest"},
    {"name": "波特兰", "lat": 45.5051, "lon": -122.6750, "state": "OR", "region": "Northwest"},
    {"name": "洛杉矶", "lat": 34.0522, "lon": -118.2437, "state": "CA", "region": "West"},
    {"name": "凤凰城", "lat": 33.4484, "lon": -112.0740, "state": "AZ", "region": "Southwest"},
    {"name": "拉斯维加斯", "lat": 36.1699, "lon": -115.1398, "state": "NV", "region": "Southwest"},
    {"name": "亚特兰大", "lat": 33.7490, "lon": -84.3880, "state": "GA", "region": "Southeast"},
    {"name": "迈阿密", "lat": 25.7617, "lon": -80.1918, "state": "FL", "region": "Southeast"},
    {"name": "休斯顿", "lat": 29.7604, "lon": -95.3698, "state": "TX", "region": "South"},
    {"name": "达拉斯", "lat": 32.7767, "lon": -96.7970, "state": "TX", "region": "South"},
]

session = requests.Session()
session.headers.update({"User-Agent": "50DayReplenishment/1.0"})


# ==================== 工具函数 ====================

def celsius(f):
    """华氏转摄氏"""
    if f is None:
        return None
    return round((f - 32) * 5 / 9)


def get_nws_point(lat, lon):
    """获取 NWS 网格点"""
    url = f"https://api.weather.gov/points/{lat},{lon}"
    try:
        r = session.get(url, timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def get_7day_forecast(grid_url):
    """获取 7 天预报"""
    try:
        r = session.get(grid_url + "/forecast", timeout=10)
        if r.status_code == 200:
            periods = r.json().get("properties", {}).get("periods", [])
            return periods[:14]  # 14 个时段 = 7 天
    except Exception:
        pass
    return []


def get_active_alerts(state_codes):
    """获取 NWS 活跃预警"""
    alerts = []
    for state in state_codes:
        try:
            url = f"https://api.weather.gov/alerts/active?area={state}"
            r = session.get(url, timeout=10)
            if r.status_code == 200:
                features = r.json().get("features", [])
                for f in features:
                    props = f.get("properties", {})
                    event = props.get("event", "")
                    severity = props.get("severity", "")
                    headline = props.get("headline", "")
                    if event:
                        alerts.append({
                            "state": state,
                            "event": event,
                            "severity": severity,
                            "headline": headline,
                        })
        except Exception:
            pass
    return alerts


def get_city_7day_data(city):
    """获取单个城市 7 天预报数据"""
    point = get_nws_point(city["lat"], city["lon"])
    if not point:
        return None

    grid_url = point["properties"]["forecastGridData"]
    periods = get_7day_forecast(grid_url)
    if not periods:
        return None

    temps = [p.get("temperature") for p in periods if p.get("temperature") is not None]
    min_temp_f = min(temps) if temps else None
    max_temp_f = max(temps) if temps else None

    return {
        "name": city["name"],
        "state": city["state"],
        "region": city["region"],
        "min_f": min_temp_f,
        "max_f": max_temp_f,
        "min_c": celsius(min_temp_f),
        "max_c": celsius(max_temp_f),
        "periods": periods,
    }


def get_nws_alerts_for_cities():
    """获取所有重点州的 NWS 活跃预警"""
    states = list(set([c["state"] for c in CITIES]))
    return get_active_alerts(states)


# ==================== 各模块函数 ====================

def build_executive_summary(all_city_data, alerts):
    """1. Executive Summary - 冬季补货风险等级"""
    lines = []
    lines.append("=" * 60)
    lines.append("📊 Executive Summary - 冬季补货风险评估")
    lines.append("=" * 60)
    lines.append("")

    cold_cities = [c for c in all_city_data if c["min_c"] and c["min_c"] <= COLD_THRESHOLD_C]
    hot_cities = [c for c in all_city_data if c["max_c"] and c["max_c"] >= HOT_THRESHOLD_C]
    severe_alerts = [a for a in alerts if a["severity"] in ("Extreme", "Severe")]
    moderate_alerts = [a for a in alerts if a["severity"] == "Moderate"]

    if severe_alerts or len(cold_cities) >= 3:
        risk_level = "🔴 HIGH - 立即启动补货"
        risk_desc = "多处极端天气预警，建议立即安排生产"
    elif moderate_alerts or len(cold_cities) >= 1:
        risk_level = "🟡 MEDIUM - 密切监控"
        risk_desc = "有预警信号，建议准备补货计划"
    elif cold_cities or hot_cities:
        risk_level = "🟢 LOW - 正常监控"
        risk_desc = "暂无极端预警，按正常节奏备货"
    else:
        risk_level = "🟢 LOW - 正常监控"
        risk_desc = "各城市温度正常，无需特殊准备"

    lines.append(f"当前风险等级: {risk_level}")
    lines.append(f"风险说明: {risk_desc}")
    lines.append("")

    if cold_cities:
        lines.append(f"⚠️ 极寒城市（<{COLD_THRESHOLD_C}°C）: {', '.join([c['name'] for c in cold_cities])}")
    if hot_cities:
        lines.append(f"⚠️ 极热城市（>{HOT_THRESHOLD_C}°C）: {', '.join([c['name'] for c in hot_cities])}")
    if severe_alerts:
        lines.append(f"🚨 严重预警: {len(severe_alerts)} 条")
    if moderate_alerts:
        lines.append(f"⚠️ 中等预警: {len(moderate_alerts)} 条")

    if not cold_cities and not hot_cities and not severe_alerts and not moderate_alerts:
        lines.append("✅ 未来 7 天各城市暂无极端温度预警")

    lines.append("")
    lines.append(f"数据来源: NWS API (api.weather.gov)")
    lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')} 北京时间")

    return "\n".join(lines)


def build_50day_replenishment_risk():
    """2. 50-Day Replenishment Risk - 长期趋势"""
    lines = []
    lines.append("")
    lines.append("=" * 60)
    lines.append("🏭 50-Day Replenishment Risk")
    lines.append("=" * 60)
    lines.append("")
    lines.append("目标: 判断是否需要启动生产")
    lines.append("")

    lines.append("⚠️ 长期趋势说明（来源: NOAA Climate Prediction Center）")
    lines.append("-" * 40)
    lines.append("NOAA 月度/季度预报仅提供趋势分类:")
    lines.append("  • Below Normal - 低于正常温度")
    lines.append("  • Near Normal - 接近正常温度")
    lines.append("  • Above Normal - 高于正常温度")
    lines.append("")
    lines.append("本系统不编造具体概率数值。")
    lines.append("")
    lines.append("如需查看官方长期趋势，请访问:")
    lines.append("  • NOAA CPC Monthly: https://www.cpc.noaa.gov/products/predictions/monthly/")
    lines.append("  • NOAA Seasonal: https://www.cpc.noaa.gov/products/people/wwhpp/proghftp.html")
    lines.append("")
    lines.append("💡 备货建议:")
    lines.append("  → 结合 NOAA 官方趋势判断是否启动生产")
    lines.append("  → 注意: 长期趋势仅供参考，最终决策请结合市场情况")

    return "\n".join(lines)


def build_45day_shipping_decision():
    """3. 45-Day Shipping Decision - 供应链提醒"""
    lines = []
    lines.append("")
    lines.append("=" * 60)
    lines.append("🚢 45-Day Shipping Decision")
    lines.append("=" * 60)
    lines.append("")
    lines.append("供应链周期:")
    lines.append("  工厂准备: ~5 天")
    lines.append("  海运/FBA入仓: ~45 天")
    lines.append("  总周期: ~50 天")
    lines.append("")

    lines.append("⚠️ 判断是否需要安排发货")
    lines.append("")
    lines.append("触发条件（满足任一即建议发货）:")
    lines.append(f"  1. 7 天内多个城市极寒预警（<{COLD_THRESHOLD_C}°C）")
    lines.append("  2. NOAA 官方发布 Arctic Blast / Polar Vortex 预警")
    lines.append("  3. 市场出现 pipe burst / freeze warning 新闻信号")
    lines.append("")
    lines.append("📋 操作建议:")
    lines.append("  • 如判断需要发货 → 立即通知工厂排产")
    lines.append("  • 提前安排海运仓位")
    lines.append("  • 关注 FBA 入仓时效")
    lines.append("")
    lines.append("⚠️ 本模块基于 7 天 NWS 预报和官方预警做判断")
    lines.append("   暂无可靠数据时显示'暂无可靠数据'")

    return "\n".join(lines)


def build_30day_market_watch():
    """4. 30-Day Market Watch - 新闻和市场信号"""
    lines = []
    lines.append("")
    lines.append("=" * 60)
    lines.append("📰 30-Day Market Watch")
    lines.append("=" * 60)
    lines.append("")
    lines.append("⚠️ 新闻/RSS 信号说明（市场参考，非官方预警）")
    lines.append("-" * 40)
    lines.append("以下关键词出现时作为市场信号参考:")
    lines.append("  • Arctic blast / Polar vortex / Deep freeze")
    lines.append("  • Winter storm / Blizzard / Ice storm")
    lines.append("  • Freeze warning / Frost advisory")
    lines.append("  • Pipe burst / Water main break")
    lines.append("  • Record cold / Historic freeze")
    lines.append("")
    lines.append("📊 新闻来源信号监测:")
    lines.append("  • 暂无可靠新闻数据源接入")
    lines.append("  → 建议手动搜索: 'Arctic blast US winter' / 'freeze warning forecast'")
    lines.append("")
    lines.append("💡 建议:")
    lines.append("  → 定期搜索 NOAA 天气预报和冬季风暴新闻")
    lines.append("  → 关注 Weather.com / AccuWeather 冬季预报")
    lines.append("  → 关注 Amazon 同类产品销量变化")
    lines.append("")
    lines.append("⚠️ 新闻信号仅供参考，不作为官方预警依据")

    return "\n".join(lines)


def build_14day_weather_risk():
    """5. 14-Day Weather Risk - NOAA CPC 展望"""
    lines = []
    lines.append("")
    lines.append("=" * 60)
    lines.append("🌡️ 14-Day Weather Risk")
    lines.append("=" * 60)
    lines.append("")
    lines.append("来源: NOAA CPC 6-10 Day & 8-14 Day Outlook")
    lines.append("网址: https://www.cpc.noaa.gov/products/predictions/610day/")
    lines.append("")
    lines.append("⚠️ 说明:")
    lines.append("  NOAA 6-10 天和 8-14 天预报提供温度趋势概率")
    lines.append("  格式: Below Normal / Near Normal / Above Normal")
    lines.append("  本系统不编造具体概率数值")
    lines.append("")
    lines.append("📋 当前 14 天趋势: 暂无可靠结构化数据")
    lines.append("  → 如需查看请访问: https://www.cpc.noaa.gov/products/predictions/610day/")
    lines.append("")
    lines.append("💡 建议:")
    lines.append("  → 每周一查看 NOAA 6-10 天温度展望")
    lines.append("  → 关注东北部、中西部极寒趋势信号")
    lines.append("  → 结合市场新闻综合判断")

    return "\n".join(lines)


def build_7day_alerts(alerts):
    """6. 7-Day Official Alerts - NWS API 活跃预警"""
    lines = []
    lines.append("")
    lines.append("=" * 60)
    lines.append("🚨 7-Day Official Alerts (NWS Active Alerts)")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"数据来源: NWS API - api.weather.gov/alerts/active")
    lines.append("")

    if not alerts:
        lines.append("✅ 目前没有 NWS 活跃预警")
    else:
        severe = [a for a in alerts if a["severity"] in ("Extreme", "Severe")]
        moderate = [a for a in alerts if a["severity"] == "Moderate"]
        other = [a for a in alerts if a["severity"] not in ("Extreme", "Severe", "Moderate")]

        if severe:
            lines.append(f"🚨 严重预警 ({len(severe)} 条):")
            for a in severe[:5]:
                lines.append(f"  • {a['event']} ({a['state']}) - {a['headline'][:50] if a['headline'] else 'N/A'}")
            lines.append("")

        if moderate:
            lines.append(f"⚠️ 中等预警 ({len(moderate)} 条):")
            for a in moderate[:5]:
                lines.append(f"  • {a['event']} ({a['state']})")
            lines.append("")

        if other:
            lines.append(f"ℹ️ 其他预警 ({len(other)} 条):")
            for a in other[:3]:
                lines.append(f"  • {a['event']} ({a['state']})")

    lines.append("")
    lines.append("💡 注意: 预警基于 NWS 官方数据，请以官方为准")

    return "\n".join(lines)


def build_7day_forecast(all_city_data):
    """7. Daily Weather Forecast - 各城市 7 天预报"""
    lines = []
    lines.append("")
    lines.append("=" * 60)
    lines.append("📍 7-Day Daily Weather Forecast")
    lines.append("=" * 60)
    lines.append("")
    lines.append("数据来源: NWS API (api.weather.gov)")
    lines.append("")

    regions = {}
    for city in all_city_data:
        region = city["region"]
        if region not in regions:
            regions[region] = []
        regions[region].append(city)

    cold_cities = []
    hot_cities = []

    for region in sorted(regions.keys()):
        cities = regions[region]
        lines.append(f"📌 {region}:")
        for c in cities:
            min_c = c["min_c"]
            max_c = c["max_c"]
            min_f = c["min_f"]
            max_f = c["max_f"]

            flag = ""
            if min_c and min_c <= COLD_THRESHOLD_C:
                flag = " ❄️ 极寒"
                cold_cities.append(c["name"])
            elif max_c and max_c >= HOT_THRESHOLD_C:
                flag = " 🔥 极热"
                hot_cities.append(c["name"])

            lines.append(f"  • {c['name']}({c['state']}): {min_c}°C ~ {max_c}°C ({min_f}°F ~ {max_f}°F){flag}")
        lines.append("")

    lines.append("-" * 40)
    lines.append("📊 极寒/极热城市汇总:")
    if cold_cities:
        lines.append(f"  ❄️ 极寒（<{COLD_THRESHOLD_C}°C）: {', '.join(cold_cities)}")
    if hot_cities:
        lines.append(f"  🔥 极热（>{HOT_THRESHOLD_C}°C）: {', '.join(hot_cities)}")
    if not cold_cities and not hot_cities:
        lines.append("  ✅ 暂无城市达到极寒/极热阈值")

    return "\n".join(lines)


def build_amazon_actions(all_city_data, alerts):
    """8. Suggested Amazon Actions - 行动建议"""
    lines = []
    lines.append("")
    lines.append("=" * 60)
    lines.append("🛒 Suggested Amazon Actions")
    lines.append("=" * 60)
    lines.append("")

    cold_cities = [c for c in all_city_data if c["min_c"] and c["min_c"] <= COLD_THRESHOLD_C]
    hot_cities = [c for c in all_city_data if c["max_c"] and c["max_c"] >= HOT_THRESHOLD_C]
    severe_alerts = [a for a in alerts if a["severity"] in ("Extreme", "Severe")]

    risk_level = "HIGH" if (severe_alerts or len(cold_cities) >= 3) else \
                 "MEDIUM" if (cold_cities or severe_alerts) else "LOW"

    lines.append(f"当前风险等级: {risk_level}")
    lines.append("")

    lines.append("📋 建议操作:")

    if risk_level == "HIGH":
        lines.append("  1. ✅ 立即启动生产 - 多处极寒预警")
        lines.append("  2. ✅ 立即安排海运/FBA发货")
        lines.append("  3. ✅ 提高 Amazon 广告预算 +50%~100%")
        lines.append("  4. ✅ 考虑提高 coupon 力度促销")
        lines.append("  5. ✅ 优化关键词: outdoor faucet cover, freeze protection, faucet freeze protector")
    elif risk_level == "MEDIUM":
        lines.append("  1. ⚠️ 准备启动生产 - 有极寒信号")
        lines.append("  2. ⚠️ 准备海运/FBA安排")
        lines.append("  3. ⚠️ 适度提高广告预算 +20%~30%")
        lines.append("  4. ⚠️ 观察 3-5 天再决定")
    else:
        lines.append("  1. ℹ️ 按正常节奏备货")
        lines.append("  2. ℹ️ 维持正常广告预算")
        lines.append("  3. ℹ️ 持续监控天气变化")

    lines.append("")
    lines.append("🎯 关键词优化建议:")
    lines.append("  • outdoor faucet cover")
    lines.append("  • freeze protection")
    lines.append("  • faucet freeze protector")
    lines.append("  • winter faucet cover")
    lines.append("  • pipe freeze protection")
    lines.append("")
    lines.append("⚠️ 注意: 建议基于 NWS 7 天预报数据，实际决策请结合市场情况")

    return "\n".join(lines)


def format_full_email(all_city_data, alerts):
    """组装完整邮件"""
    parts = []

    parts.append(f"🏭 {SYSTEM_NAME}")
    parts.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')} 北京时间")
    parts.append("=" * 60)

    parts.append(build_executive_summary(all_city_data, alerts))
    parts.append(build_50day_replenishment_risk())
    parts.append(build_45day_shipping_decision())
    parts.append(build_30day_market_watch())
    parts.append(build_14day_weather_risk())
    parts.append(build_7day_alerts(alerts))
    parts.append(build_7day_forecast(all_city_data))
    parts.append(build_amazon_actions(all_city_data, alerts))

    parts.append("")
    parts.append("=" * 60)
    parts.append("📊 系统说明")
    parts.append("-" * 40)
    parts.append("• 7天预报: NWS API ✅ 可靠")
    parts.append("• 14天趋势: NOAA CPC 暂无可靠结构化数据")
    parts.append("• 30天/50天趋势: NOAA 暂无可靠结构化数据")
    parts.append("• 新闻信号: 暂无可靠数据源接入")
    parts.append("")
    parts.append("⚠️ 本系统仅供参考，备货决策请结合实际情况")
    parts.append("   不允许编造具体温度或概率数据")

    return "\n".join(parts)


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
    msg["Subject"] = "🏭 50天冬季备货预警"
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


def main():
    print("=" * 60)
    print(f"运行 {SYSTEM_NAME}...")
    print("=" * 60)

    print("\n📍 Step 1: 获取 7 天城市预报（NWS API）...")
    all_city_data = []
    for city in CITIES:
        try:
            print(f"  获取 {city['name']}...")
            data = get_city_7day_data(city)
            if data:
                all_city_data.append(data)
                print(f"    {city['name']}: {data['min_c']}°C ~ {data['max_c']}°C")
            time.sleep(0.3)
        except Exception as e:
            print(f"    获取 {city['name']} 失败: {e}")

    print(f"\n成功获取 {len(all_city_data)} 个城市数据")

    print("\n🚨 Step 2: 获取 NWS 活跃预警...")
    alerts = get_nws_alerts_for_cities()
    print(f"找到 {len(alerts)} 条活跃预警")

    print("\n📧 Step 3: 生成并发送邮件...")
    email_content = format_full_email(all_city_data, alerts)
    print(email_content)

    send_email(email_content)
    print("\n完成！")


if __name__ == "__main__":
    main()
