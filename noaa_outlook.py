#!/usr/bin/env python3
"""
Dual-Product Weather & Replenishment Alert System

产品线 1: Outdoor Faucet Cover — 冬季户外水龙头保暖罩
产品线 2: Air Vent Deflector — 空调/暖气温控通风导流罩

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
- 高温预警仅适用于 Air Vent Deflector，不适用于 Faucet Cover
- Faucet Cover 核心高风险阈值: ≤14°F / -10°C
"""

import requests
from datetime import datetime, timedelta
import os
import time
import re

# ==================== 常量 ====================
SYSTEM_NAME = "Dual-Product Weather & Replenishment Alert System"

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


def get_heat_duration(periods):
    """计算高温持续天数（连续多少天日最高温 ≥ 90°F / 32°C）"""
    if not periods:
        return None

    # 调试：打印第一个 period 的所有 key
    print(f"  [DEBUG] periods count: {len(periods)}, keys sample: {list(periods[0].keys()) if periods else 'empty'}")

    # 按日历天分组，取每天的最高温
    daily_max = {}
    for p in periods:
        start = p.get("startTime", "")
        if not start:
            continue
        # 取 YYYY-MM-DD 部分
        day = start[:10]
        temp = p.get("temperature")
        if temp is None:
            continue
        if day not in daily_max or temp > daily_max[day]:
            daily_max[day] = temp

    if not daily_max:
        return None

    # 找出连续多少天 ≥ 90°F
    hot_days = sorted([day for day, temp in daily_max.items() if temp >= 90])
    if not hot_days:
        return None

    # 计算连续天数
    max_consecutive = 1
    current_streak = 1
    current_start = hot_days[0]
    best_start = hot_days[0]
    best_end = hot_days[0]

    prev_day = hot_days[0]
    for day in hot_days[1:]:
        from datetime import datetime, timedelta
        prev_dt = datetime.strptime(prev_day, "%Y-%m-%d")
        curr_dt = datetime.strptime(day, "%Y-%m-%d")
        if (curr_dt - prev_dt).days == 1:
            current_streak += 1
        else:
            if current_streak > max_consecutive:
                max_consecutive = current_streak
                best_start = current_start
                best_end = prev_day
            current_streak = 1
            current_start = day
        prev_day = day

    if current_streak > max_consecutive:
        max_consecutive = current_streak
        best_start = current_start
        best_end = day

    # 计算起始日（连续段的第一天）
    from datetime import datetime, timedelta
    end_dt = datetime.strptime(best_end, "%Y-%m-%d")
    start_dt = end_dt - timedelta(days=max_consecutive - 1)

    return {
        "days": max_consecutive,
        "start_date": start_dt.strftime("%Y-%m-%d"),
        "end_date": best_end,
        "peak_temp_f": max(temp for day, temp in daily_max.items() if day >= best_start and day <= best_end),
    }


def format_temp_period(city_data, period_key):
    """格式化城市温度峰值发生的具体时间段信息"""
    p = city_data.get(period_key)
    is_heat = period_key == "peak_heat_period"
    temp_f = city_data.get("max_f" if is_heat else "min_f")
    temp_c = city_data.get("max_c" if is_heat else "min_c")

    if not p:
        temp_f_str = f"{temp_f}°F" if temp_f is not None else "N/A"
        temp_c_str = f"{temp_c}°C" if temp_c is not None else "N/A"
        label = "最高温" if is_heat else "最低温"
        return f"{city_data['name']}, {city_data['state']}: {label} {temp_f_str} / {temp_c_str} — 暂无官方时间"

    name = p.get("name", "")
    temp = p.get("temperature")
    unit = p.get("temperatureUnit", "F")
    start = p.get("startTime", "")[:16] if p.get("startTime") else "暂无官方时间"
    end = p.get("endTime", "")[:16] if p.get("endTime") else "暂无官方时间"
    forecast = p.get("shortForecast", "")

    temp_c_calc = celsius(temp) if temp is not None else "N/A"
    temp_str = f"{temp}°{unit}" if temp is not None else "N/A"
    temp_c_str = f"{temp_c_calc}°C" if temp_c_calc != "N/A" else ""

    lines = []
    lines.append(f"{city_data['name']}, {city_data['state']}")
    if is_heat:
        lines.append(f"  最高温: {temp_str} / {temp_c_str}")
    else:
        lines.append(f"  最低温: {temp_str} / {temp_c_str}")
    lines.append(f"  预报时段: {name if name else '暂无官方时间'}")
    lines.append(f"  开始时间: {start}")
    lines.append(f"  结束时间: {end}")
    if forecast:
        lines.append(f"  天气状况: {forecast}")
    lines.append(f"  来源: NWS API")
    return "\n".join(lines)


def format_heat_city(city_data):
    """格式化高温城市信息（包含持续天数）"""
    dur = city_data.get("heat_duration")
    peak = city_data.get("peak_heat_period")
    max_f = city_data.get("max_f")
    max_c = city_data.get("max_c")

    lines = []
    lines.append(f"{city_data['name']}, {city_data['state']}")

    if dur:
        lines.append(f"  最高温: {max_f}°F / {max_c}°C")
        lines.append(f"  高温持续: {dur['days']} 天（{dur['start_date'][5:].replace('-', '/')} ~ {dur['end_date'][5:].replace('-', '/')}）")
    elif peak:
        temp = peak.get("temperature")
        unit = peak.get("temperatureUnit", "F")
        temp_str = f"{temp}°{unit}" if temp is not None else "N/A"
        temp_c = celsius(temp) if temp is not None else "N/A"
        temp_c_str = f"{temp_c}°C" if temp_c != "N/A" else ""
        name = peak.get("name", "")
        start = peak.get("startTime", "")[:16] if peak.get("startTime") else "暂无官方时间"
        end = peak.get("endTime", "")[:16] if peak.get("endTime") else "暂无官方时间"
        lines.append(f"  最高温: {temp_str} / {temp_c_str}")
        lines.append(f"  预报时段: {name if name else '暂无官方时间'}")
        lines.append(f"  开始时间: {start}")
        lines.append(f"  结束时间: {end}")
    else:
        if max_f is not None:
            lines.append(f"  最高温: {max_f}°F / {max_c}°C")
        lines.append(f"  高温持续: 暂无官方时间")

    lines.append(f"  来源: NWS API")
    return "\n".join(lines)


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
                    area = props.get("areaDesc", "")
                    effective = props.get("effective", "")
                    onset = props.get("onset", "")
                    expires = props.get("expires", "")
                    ends = props.get("ends", "")
                    if event:
                        alerts.append({
                            "state": state,
                            "event": event,
                            "severity": severity,
                            "headline": headline,
                            "area": area,
                            "effective": effective,
                            "onset": onset,
                            "expires": expires,
                            "ends": ends,
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
    min_temp_c = celsius(min_temp_f)
    max_temp_c = celsius(max_temp_f)

    # 找出最低/最高温对应的 period（用于显示具体时间）
    def make_period_summary(p):
        if not p:
            return None
        return {
            "name": p.get("name", ""),
            "temperature": p.get("temperature"),
            "temperatureUnit": p.get("temperatureUnit", "F"),
            "startTime": p.get("startTime", ""),
            "endTime": p.get("endTime", ""),
            "shortForecast": p.get("shortForecast", ""),
        }

    peak_heat_period = None
    peak_cold_period = None
    if max_temp_f is not None:
        for p in periods:
            if p.get("temperature") == max_temp_f:
                peak_heat_period = make_period_summary(p)
                break
    if min_temp_f is not None:
        for p in periods:
            if p.get("temperature") == min_temp_f:
                peak_cold_period = make_period_summary(p)
                break

    # 计算高温持续天数
    heat_duration = get_heat_duration(periods) if vent_heat else None

    # --- Outdoor Faucet Cover 风险等级 ---
    # 14°F = -10°C: 核心补货预警 | 23°F = -5°C: 中等风险 | 32°F = 0°C: 低温关注
    faucet_risk = "none"
    if min_temp_f is not None:
        if min_temp_f <= 5:       # ≤5°F / -15°C → Critical
            faucet_risk = "critical"
        elif min_temp_f <= 14:    # ≤14°F / -10°C → High
            faucet_risk = "high"
        elif min_temp_f <= 23:    # ≤23°F / -5°C → Moderate
            faucet_risk = "moderate"
        elif min_temp_f <= 32:    # ≤32°F / 0°C → Watch
            faucet_risk = "watch"

    # --- Air Vent Deflector 冷暖需求信号 ---
    # 高温需求: ≥90°F / 32°C
    # 低温需求: ≤45°F / 7°C → Watch | ≤32°F / 0°C → Strong
    vent_heat = max_temp_f >= 90 if max_temp_f is not None else False
    vent_cold_tier = "none"
    if min_temp_f is not None:
        if min_temp_f <= 32:
            vent_cold_tier = "strong"   # ≤32°F / 0°C
        elif min_temp_f <= 45:
            vent_cold_tier = "watch"    # ≤45°F / 7°C

    return {
        "name": city["name"],
        "state": city["state"],
        "region": city["region"],
        "min_f": min_temp_f,
        "max_f": max_temp_f,
        "min_c": min_temp_c,
        "max_c": max_temp_c,
        "periods": periods,
        "faucet_risk": faucet_risk,
        "vent_heat": vent_heat,
        "vent_cold": vent_cold_tier,
        "peak_heat_period": peak_heat_period,
        "peak_cold_period": peak_cold_period,
        "heat_duration": heat_duration,
    }


def get_nws_alerts_for_cities():
    """获取所有重点州的 NWS 活跃预警"""
    states = list(set([c["state"] for c in CITIES]))
    return get_active_alerts(states)


# ==================== 各模块函数 ====================

def build_executive_summary(all_city_data, alerts):
    """1. Executive Summary - 分别评估两个产品线"""
    lines = []
    lines.append("=" * 60)
    lines.append("📊 Executive Summary - 双产品线风险评估")
    lines.append("=" * 60)
    lines.append("")

    # ---- Outdoor Faucet Cover ----
    faucet_critical = [c for c in all_city_data if c.get("faucet_risk") == "critical"]
    faucet_high = [c for c in all_city_data if c.get("faucet_risk") == "high"]
    faucet_moderate = [c for c in all_city_data if c.get("faucet_risk") == "moderate"]
    faucet_watch = [c for c in all_city_data if c.get("faucet_risk") == "watch"]

    FAUCET_COLD_ALERTS = {
        "Freeze Warning", "Hard Freeze Warning", "Winter Storm Warning",
        "Winter Storm Watch", "Ice Storm Warning", "Wind Chill Warning",
        "Extreme Cold Warning", "Frost Advisory", "Freeze Watch",
        "Wind Chill Advisory", "Heavy Snow Warning", "Blizzard Warning",
    }
    faucet_alerts = [a for a in alerts if a["event"] in FAUCET_COLD_ALERTS]
    faucet_severe = [a for a in faucet_alerts if a["severity"] in ("Extreme", "Severe")]

    if faucet_critical or len(faucet_severe) >= 2:
        faucet_level = "🔴 CRITICAL - 爆单风险，立即补货"
        faucet_desc = "多城市≤5°F(-15°C)，强烈建议立即生产补货"
    elif faucet_high or len(faucet_severe) >= 1:
        faucet_level = "🔴 HIGH - 核心补货预警"
        faucet_desc = "多城市≤14°F(-10°C)，建议立即安排生产"
    elif faucet_moderate:
        faucet_level = "🟡 MEDIUM - 中等风险"
        faucet_desc = "多城市≤23°F(-5°C)，建议准备补货计划"
    elif faucet_watch:
        faucet_level = "🟢 LOW - 低温关注"
        faucet_desc = "多城市≤32°F(0°C)，正常监控"
    else:
        faucet_level = "🟢 LOW - 正常"
        faucet_desc = "暂无冰冻风险信号"

    lines.append("【Outdoor Faucet Cover – 冬季冻裂风险】")
    lines.append(f"  风险等级: {faucet_level}")
    lines.append(f"  说明: {faucet_desc}")
    if faucet_critical:
        lines.append("  Critical 城市(≤5°F/-15°C):")
        for c in faucet_critical:
            lines.append(format_temp_period(c, "peak_cold_period"))
    if faucet_high:
        lines.append("  高风险城市(≤14°F/-10°C):")
        for c in faucet_high:
            lines.append(format_temp_period(c, "peak_cold_period"))
    if faucet_moderate:
        lines.append("  中等风险城市(≤23°F/-5°C):")
        for c in faucet_moderate:
            lines.append(format_temp_period(c, "peak_cold_period"))
    if faucet_watch:
        lines.append("  低温关注城市(≤32°F/0°C):")
        for c in faucet_watch:
            lines.append(format_temp_period(c, "peak_cold_period"))
    if faucet_severe:
        lines.append(f"  严重/极端冻害预警: {len(faucet_severe)} 条")
    if not any([faucet_critical, faucet_high, faucet_moderate, faucet_watch, faucet_severe]):
        lines.append("  ✅ 未来 7 天各城市暂无冰冻预警")
    lines.append("")

    # ---- Air Vent Deflector ----
    vent_heat_cities = [c for c in all_city_data if c.get("vent_heat")]
    vent_cold_strong = [c for c in all_city_data if c.get("vent_cold") == "strong"]
    vent_cold_watch = [c for c in all_city_data if c.get("vent_cold") == "watch"]

    VENT_HEAT_ALERTS = {"Heat Advisory", "Excessive Heat Warning", "Heat Wave", "Excessive Heat Watch"}
    VENT_COLD_ALERTS = {"Cold Wave", "Winter Storm Warning", "Winter Storm Watch",
                        "Extreme Cold Warning", "Wind Chill Warning", "Hard Freeze Warning"}
    vent_heat_alerts = [a for a in alerts if a["event"] in VENT_HEAT_ALERTS]
    vent_cold_alerts = [a for a in alerts if a["event"] in VENT_COLD_ALERTS]
    vent_all_relevant = vent_heat_alerts + vent_cold_alerts

    if vent_heat_cities or vent_heat_alerts:
        vent_level = "🟠 HIGH - 夏季空调需求旺盛"
        vent_desc = "多城市≥90°F(32°C)高温，空调/导风罩需求上升"
    elif vent_cold_strong or vent_cold_alerts:
        vent_level = "🟠 HIGH - 冬季采暖需求旺盛"
        vent_desc = "多城市≤32°F(0°C)，HVAC 强采暖需求，导风罩需求上升"
    elif vent_cold_watch:
        vent_level = "🟡 MODERATE - 冬季采暖需求初现"
        vent_desc = "多城市≤45°F(7°C)，HVAC 采暖开始使用，需求温和上升"
    elif any(c.get("vent_heat") or c.get("vent_cold") not in ("none", False) for c in all_city_data):
        vent_level = "🟡 MODERATE - 温和气候需求"
        vent_desc = "温差适中，HVAC 需求一般"
    else:
        vent_level = "🟢 LOW - 正常"
        vent_desc = "暂无强烈 HVAC 需求信号"

    lines.append("【Air Vent Deflector – HVAC 冷暖需求信号】")
    lines.append(f"  需求等级: {vent_level}")
    lines.append(f"  说明: {vent_desc}")
    if vent_heat_cities:
        lines.append("  🔥 高温城市(≥90°F/32°C):")
        for c in vent_heat_cities:
            lines.append(format_heat_city(c))
    if vent_cold_strong:
        lines.append("  ❄️ 强采暖城市(≤32°F/0°C):")
        for c in vent_cold_strong:
            lines.append(format_temp_period(c, "peak_cold_period"))
    if vent_cold_watch:
        lines.append("  ⚠️ 采暖 Watch 城市(≤45°F/7°C):")
        for c in vent_cold_watch:
            lines.append(format_temp_period(c, "peak_cold_period"))
    if vent_heat_alerts:
        lines.append(f"  高温预警: {len(vent_heat_alerts)} 条")
    if vent_cold_alerts:
        lines.append(f"  低温/寒潮预警: {len(vent_cold_alerts)} 条")
    if not vent_heat_cities and not vent_cold_strong and not vent_cold_watch and not vent_all_relevant:
        lines.append("  ✅ 暂无强烈 HVAC 需求信号")
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


def build_faucet_cover_risk(all_city_data, alerts):
    """2. Outdoor Faucet Cover – Winter Freeze Risk Detail"""
    FAUCET_COLD_ALERTS = {
        "Freeze Warning", "Hard Freeze Warning", "Winter Storm Warning",
        "Winter Storm Watch", "Ice Storm Warning", "Wind Chill Warning",
        "Extreme Cold Warning", "Frost Advisory", "Freeze Watch",
        "Wind Chill Advisory", "Heavy Snow Warning", "Blizzard Warning",
    }
    lines = []
    lines.append("")
    lines.append("=" * 60)
    lines.append("❄️ Outdoor Faucet Cover – Winter Freeze Risk")
    lines.append("=" * 60)
    lines.append("")
    lines.append("产品用途: 冬季户外水龙头保暖罩，防止冻裂")
    lines.append("核心阈值: ≤14°F/-10°C 触发补货 | ≤5°F/-15°C 爆单风险")
    lines.append("⚠️ 高温预警不适用于本产品")
    lines.append("")

    faucet_cities_critical = [c for c in all_city_data if c.get("faucet_risk") == "critical"]
    faucet_cities_high = [c for c in all_city_data if c.get("faucet_risk") == "high"]
    faucet_cities_moderate = [c for c in all_city_data if c.get("faucet_risk") == "moderate"]
    faucet_cities_watch = [c for c in all_city_data if c.get("faucet_risk") == "watch"]
    faucet_alerts = [a for a in alerts if a["event"] in FAUCET_COLD_ALERTS]
    faucet_severe = [a for a in faucet_alerts if a["severity"] in ("Extreme", "Severe")]
    faucet_moderate_a = [a for a in faucet_alerts if a["severity"] == "Moderate"]

    if faucet_cities_critical:
        lines.append("🚨 CRITICAL – 爆单风险城市:")
        for c in faucet_cities_critical:
            lines.append(format_temp_period(c, "peak_cold_period"))
        lines.append("")

    if faucet_cities_high:
        lines.append("🔴 HIGH – 核心补货风险城市:")
        for c in faucet_cities_high:
            lines.append(format_temp_period(c, "peak_cold_period"))
        lines.append("")

    if faucet_cities_moderate:
        lines.append("🟡 MODERATE – 中等风险城市:")
        for c in faucet_cities_moderate:
            lines.append(format_temp_period(c, "peak_cold_period"))
        lines.append("")

    if faucet_cities_watch:
        lines.append("🟢 WATCH – 低温关注城市:")
        for c in faucet_cities_watch:
            lines.append(format_temp_period(c, "peak_cold_period"))
        lines.append("")

    if faucet_alerts:
        lines.append("📢 相关 NWS 预警:")
        for a in faucet_alerts[:8]:
            sev_cn = {"Extreme": "极端", "Severe": "严重", "Moderate": "中等"}.get(a["severity"], a["severity"])
            lines.append(f"  • [{sev_cn}] {a['event']} - {a['state']}")
        lines.append("")
    else:
        lines.append("📢 NWS 冻害预警: 暂无\n")

    lines.append("数据来源: NWS API (api.weather.gov)")
    return "\n".join(lines)


def build_vent_deflector_signal(all_city_data, alerts):
    """3. Air Vent Deflector – HVAC Demand Signal Detail"""
    VENT_HEAT_ALERTS = {"Heat Advisory", "Excessive Heat Warning", "Heat Wave", "Excessive Heat Watch"}
    VENT_COLD_ALERTS = {"Cold Wave", "Winter Storm Warning", "Winter Storm Watch",
                        "Extreme Cold Warning", "Wind Chill Warning", "Hard Freeze Warning"}
    lines = []
    lines.append("")
    lines.append("=" * 60)
    lines.append("🔥 Air Vent Deflector – HVAC Demand Signal")
    lines.append("=" * 60)
    lines.append("")
    lines.append("产品用途: 空调/暖气温控通风导流罩")
    lines.append("需求信号: 高温(冷气需求) + 低温(暖气需求)")
    lines.append("低温分级: ≤45°F/7°C → Watch | ≤32°F/0°C → Strong | Winter Storm/Cold Wave 等 → 寒潮信号")
    lines.append("⚠️ 冷气和暖气需求都计入 HVAC 需求")
    lines.append("")

    vent_heat_cities = [c for c in all_city_data if c.get("vent_heat")]
    vent_cold_strong = [c for c in all_city_data if c.get("vent_cold") == "strong"]
    vent_cold_watch = [c for c in all_city_data if c.get("vent_cold") == "watch"]
    vent_heat_alerts = [a for a in alerts if a["event"] in VENT_HEAT_ALERTS]
    vent_cold_alerts = [a for a in alerts if a["event"] in VENT_COLD_ALERTS]

    if vent_heat_cities:
        lines.append("🔥 高温需求城市 (≥90°F/32°C) – 冷气市场:")
        for c in vent_heat_cities:
            lines.append(format_heat_city(c))
        lines.append("")

    if vent_cold_strong:
        lines.append("❄️ 强采暖需求城市 (≤32°F/0°C):")
        for c in vent_cold_strong:
            lines.append(format_temp_period(c, "peak_cold_period"))
        lines.append("")

    if vent_cold_watch:
        lines.append("⚠️ 采暖 Watch 城市 (≤45°F/7°C):")
        for c in vent_cold_watch:
            lines.append(format_temp_period(c, "peak_cold_period"))
        lines.append("")

    if not vent_heat_cities and not vent_cold_strong and not vent_cold_watch:
        lines.append("🟢 暂无强烈 HVAC 需求城市")
        lines.append("")

    if vent_heat_alerts:
        lines.append("📢 相关高温预警:")
        for a in vent_heat_alerts[:5]:
            lines.append(f"  • {a['event']} - {a['state']}")
        lines.append("")

    if vent_cold_alerts:
        lines.append("📢 寒潮/低温预警 (Winter Storm/Cold Wave/Wind Chill 等):")
        for a in vent_cold_alerts[:5]:
            lines.append(f"  • {a['event']} - {a['state']}")
        lines.append("")

    if not vent_heat_alerts and not vent_cold_alerts:
        lines.append("📢 NWS HVAC 相关预警: 暂无")
        lines.append("")

    lines.append("数据来源: NWS API (api.weather.gov)")
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

        # Alert Details
        lines.append("")
        lines.append("== Alert Details ==")
        for a in alerts:
            effective_str = a.get("effective", "")[:16] if a.get("effective") else "暂无官方时间"
            onset_str = a.get("onset", "")[:16] if a.get("onset") else "暂无官方时间"
            expires_str = a.get("expires", "")[:16] if a.get("expires") else "暂无官方时间"
            ends_str = a.get("ends", "")[:16] if a.get("ends") else "暂无官方时间"
            sev_cn = {"Extreme": "极端", "Severe": "严重", "Moderate": "中等", "Minor": "轻微", "Unknown": "未知"}.get(a["severity"], a["severity"])
            lines.append(f"  • 预警类型: {a['event']}")
            lines.append(f"    影响地区: {a.get('area', a['state'])}")
            lines.append(f"    严重等级: {sev_cn}")
            lines.append(f"    生效时间: {effective_str}")
            lines.append(f"    开始时间: {onset_str}")
            lines.append(f"    到期时间: {expires_str}")
            lines.append(f"    结束时间: {ends_str}")
            if a.get("headline"):
                lines.append(f"    官方标题: {a['headline'][:80]}")
            lines.append(f"    来源: NWS API")
            lines.append("")

    lines.append("")
    lines.append("💡 注意: 预警基于 NWS 官方数据，请以官方为准")

    return "\n".join(lines)


def build_7day_forecast(all_city_data):
    """7. Daily Weather Forecast - 各城市 7 天预报（含产品需求标记）"""
    lines = []
    lines.append("")
    lines.append("=" * 60)
    lines.append("📍 7-Day City Weather Forecast (with Product Signals)")
    lines.append("=" * 60)
    lines.append("")
    lines.append("产品信号说明:")
    lines.append("  ❄️ [Faucet Critical] ≤5°F/-15°C — Faucet Cover 爆单风险")
    lines.append("  ❄️ [Faucet HIGH] ≤14°F/-10°C — Faucet Cover 核心补货")
    lines.append("  ⚠️ [Faucet Watch] ≤32°F/0°C — Faucet Cover 低温关注")
    lines.append("  🔥 [Vent Heat] ≥90°F/32°C — Vent Deflector 高温需求")
    lines.append("  ❄️ [Vent Cold Strong] ≤32°F/0°C — Vent Deflector 强采暖需求")
    lines.append("  ⚠️ [Vent Cold Watch] ≤45°F/7°C — Vent Deflector 采暖 Watch")
    lines.append("")

    regions = {}
    for city in all_city_data:
        region = city["region"]
        if region not in regions:
            regions[region] = []
        regions[region].append(city)

    faucet_critical_cities = []
    faucet_high_cities = []
    faucet_watch_cities = []
    vent_heat_cities = []
    vent_cold_strong_cities = []
    vent_cold_watch_cities = []

    for region in sorted(regions.keys()):
        cities = regions[region]
        lines.append(f"📌 {region}:")
        for c in cities:
            min_c = c["min_c"]
            max_c = c["max_c"]
            min_f = c["min_f"]
            max_f = c["max_f"]

            tags = []
            risk = c.get("faucet_risk", "none")
            if risk == "critical":
                tags.append("❄️ [Faucet Critical]")
                faucet_critical_cities.append(c["name"])
            elif risk == "high":
                tags.append("❄️ [Faucet HIGH]")
                faucet_high_cities.append(c["name"])
            elif risk == "moderate":
                tags.append("⚠️ [Faucet Mod]")
            elif risk == "watch":
                tags.append("⚠️ [Faucet Watch]")
                faucet_watch_cities.append(c["name"])

            if c.get("vent_heat"):
                tags.append("🔥 [Vent Heat]")
                vent_heat_cities.append(c["name"])
            vent_cold_tier = c.get("vent_cold", "none")
            if vent_cold_tier == "strong":
                tags.append("❄️ [Vent Cold Strong]")
                vent_cold_strong_cities.append(c["name"])
            elif vent_cold_tier == "watch":
                tags.append("⚠️ [Vent Cold Watch]")
                vent_cold_watch_cities.append(c["name"])

            flag_str = " ".join(tags) if tags else ""
            lines.append(f"  • {c['name']}({c['state']}): {min_c}°C ~ {max_c}°C ({min_f}°F ~ {max_f}°F) {flag_str}")
        lines.append("")

    # Summary by product
    lines.append("-" * 40)
    lines.append("📊 Outdoor Faucet Cover 温度风险汇总:")
    if faucet_critical_cities:
        lines.append("  ❄️ Critical (≤5°F/-15°C):")
        for name in faucet_critical_cities:
            city = next((c for c in all_city_data if c["name"] == name), None)
            if city:
                lines.append(format_temp_period(city, "peak_cold_period"))
    if faucet_high_cities:
        lines.append("  ❄️ HIGH (≤14°F/-10°C):")
        for name in faucet_high_cities:
            city = next((c for c in all_city_data if c["name"] == name), None)
            if city:
                lines.append(format_temp_period(city, "peak_cold_period"))
    if faucet_watch_cities:
        lines.append("  ⚠️ Watch (≤32°F/0°C):")
        for name in faucet_watch_cities:
            city = next((c for c in all_city_data if c["name"] == name), None)
            if city:
                lines.append(format_temp_period(city, "peak_cold_period"))
    if not faucet_critical_cities and not faucet_high_cities and not faucet_watch_cities:
        lines.append("  🟢 暂无冰冻风险城市")

    lines.append("")
    lines.append("📊 Air Vent Deflector HVAC 需求汇总:")
    if vent_heat_cities:
        lines.append("  🔥 高温需求 (≥90°F/32°C):")
        for name in vent_heat_cities:
            city = next((c for c in all_city_data if c["name"] == name), None)
            if city:
                lines.append(format_heat_city(city))
    if vent_cold_strong_cities:
        lines.append("  ❄️ 强采暖需求 (≤32°F/0°C):")
        for name in vent_cold_strong_cities:
            city = next((c for c in all_city_data if c["name"] == name), None)
            if city:
                lines.append(format_temp_period(city, "peak_cold_period"))
    if vent_cold_watch_cities:
        lines.append("  ⚠️ 采暖 Watch (≤45°F/7°C):")
        for name in vent_cold_watch_cities:
            city = next((c for c in all_city_data if c["name"] == name), None)
            if city:
                lines.append(format_temp_period(city, "peak_cold_period"))
    if not vent_heat_cities and not vent_cold_strong_cities and not vent_cold_watch_cities:
        lines.append("  🟢 暂无强烈 HVAC 需求城市")

    return "\n".join(lines)


def build_amazon_actions(all_city_data, alerts):
    """10. Suggested Amazon Actions - 双产品行动建议"""
    lines = []
    lines.append("")
    lines.append("=" * 60)
    lines.append("🛒 Suggested Amazon Actions (Dual Product)")
    lines.append("=" * 60)
    lines.append("")

    # ---- Outdoor Faucet Cover ----
    FAUCET_COLD_ALERTS = {
        "Freeze Warning", "Hard Freeze Warning", "Winter Storm Warning",
        "Winter Storm Watch", "Ice Storm Warning", "Wind Chill Warning",
        "Extreme Cold Warning", "Frost Advisory", "Freeze Watch",
        "Wind Chill Advisory", "Heavy Snow Warning", "Blizzard Warning",
    }
    faucet_cold_alerts = [a for a in alerts if a["event"] in FAUCET_COLD_ALERTS]
    faucet_severe = [a for a in faucet_cold_alerts if a["severity"] in ("Extreme", "Severe")]
    faucet_critical = [c for c in all_city_data if c.get("faucet_risk") == "critical"]
    faucet_high = [c for c in all_city_data if c.get("faucet_risk") == "high"]

    if faucet_critical or len(faucet_severe) >= 2:
        f_risk = "CRITICAL"
    elif faucet_high or len(faucet_severe) >= 1:
        f_risk = "HIGH"
    elif [c for c in all_city_data if c.get("faucet_risk") in ("moderate", "watch")]:
        f_risk = "MEDIUM"
    else:
        f_risk = "LOW"

    lines.append("【Outdoor Faucet Cover】")
    lines.append(f"  风险等级: {f_risk}")
    lines.append("  📋 建议操作:")

    if f_risk == "CRITICAL":
        lines.append("    ✅ 立即启动生产（爆单风险）")
        lines.append("    ✅ 立即安排海运/FBA 加急")
        lines.append("    ✅ 广告预算提高到 +100%")
        lines.append("    ✅ Coupon 力度最大化")
        lines.append("    ✅ 备货量按 3 倍日常量安排")
    elif f_risk == "HIGH":
        lines.append("    ✅ 立即启动生产")
        lines.append("    ✅ 立即安排海运/FBA")
        lines.append("    ✅ 广告预算提高 +50%~100%")
        lines.append("    ✅ Coupon 力度提高")
        lines.append("    ✅ 备货量按 2 倍日常量安排")
    elif f_risk == "MEDIUM":
        lines.append("    ⚠️ 准备启动生产")
        lines.append("    ⚠️ 准备海运/FBA安排")
        lines.append("    ⚠️ 广告预算提高 +20%~30%")
        lines.append("    ⚠️ 观察 3-5 天再决定")
    else:
        lines.append("    ℹ️ 按正常节奏备货")
        lines.append("    ℹ️ 维持正常广告预算")

    lines.append("  🎯 Faucet Cover 关键词:")
    lines.append("    • outdoor faucet cover")
    lines.append("    • freeze protection")
    lines.append("    • faucet freeze protector")
    lines.append("    • winter faucet cover")
    lines.append("    • pipe freeze protection")
    lines.append("")

    # ---- Air Vent Deflector ----
    vent_heat_cities = [c for c in all_city_data if c.get("vent_heat")]
    vent_cold_strong = [c for c in all_city_data if c.get("vent_cold") == "strong"]
    vent_cold_watch = [c for c in all_city_data if c.get("vent_cold") == "watch"]

    VENT_HEAT_ALERTS = {"Heat Advisory", "Excessive Heat Warning", "Heat Wave", "Excessive Heat Watch"}
    VENT_COLD_ALERTS = {"Cold Wave", "Winter Storm Warning", "Winter Storm Watch",
                        "Extreme Cold Warning", "Wind Chill Warning", "Hard Freeze Warning"}
    vent_heat_alerts = [a for a in alerts if a["event"] in VENT_HEAT_ALERTS]
    vent_cold_alerts = [a for a in alerts if a["event"] in VENT_COLD_ALERTS]

    if vent_heat_cities or vent_heat_alerts:
        v_risk = "HIGH (Heat)"
    elif vent_cold_strong or vent_cold_alerts:
        v_risk = "HIGH (Cold)"
    elif vent_cold_watch:
        v_risk = "MODERATE (Cold Watch)"
    elif any(c.get("vent_heat") or c.get("vent_cold") not in ("none", False) for c in all_city_data):
        v_risk = "MODERATE"
    else:
        v_risk = "LOW"

    lines.append("【Air Vent Deflector – HVAC 需求】")
    lines.append(f"  需求等级: {v_risk}")
    lines.append("  📋 建议操作:")

    if "HIGH" in v_risk:
        lines.append("    ✅ 广告预算提高 +50%~100%（HVAC 需求旺盛）")
        lines.append("    ✅ 主图/文案突出'冷气导流'或'采暖节能'场景")
        lines.append("    ✅ 考虑增加 coupon 吸引点击")
        lines.append("    ✅ 优化以下关键词:")
    elif v_risk == "MODERATE":
        lines.append("    ⚠️ 广告预算适度提高 +20%~30%")
        lines.append("    ⚠️ 观察天气变化趋势")
    else:
        lines.append("    ℹ️ 维持正常广告预算")
        lines.append("    ℹ️ 持续监控天气变化")

    lines.append("  🎯 Vent Deflector 夏季关键词:")
    lines.append("    • air vent deflector")
    lines.append("    • ac vent cover")
    lines.append("    • hvac vent cover")
    lines.append("    • return air vent cover")
    lines.append("    • vent cover for winter")
    lines.append("  🎯 Vent Deflector 冬季关键词:")
    lines.append("    • furnace vent cover")
    lines.append("    • heating vent deflector")
    lines.append("    • hot air vent cover")
    lines.append("    • dryer vent cover")
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
    parts.append(build_faucet_cover_risk(all_city_data, alerts))
    parts.append(build_vent_deflector_signal(all_city_data, alerts))
    parts.append(build_7day_alerts(alerts))
    parts.append(build_7day_forecast(all_city_data))
    parts.append(build_50day_replenishment_risk())
    parts.append(build_45day_shipping_decision())
    parts.append(build_30day_market_watch())
    parts.append(build_14day_weather_risk())
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
    msg["Subject"] = "🏭 双产品线天气预警与备货建议"
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
