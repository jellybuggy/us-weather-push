# 美国各区域代表城市配置
# 每个区域选2个代表城市，经纬度用于调用 NWS API

REGIONS = {
    "东北部": {
        "states": ["NY", "MA", "PA", "NJ", "CT"],
        "cities": [
            {"name": "纽约", "en": "New York", "lat": 40.7128, "lon": -74.0060},
            {"name": "波士顿", "en": "Boston", "lat": 42.3601, "lon": -71.0589},
        ],
    },
    "东南部": {
        "states": ["FL", "GA", "SC", "NC"],
        "cities": [
            {"name": "迈阿密", "en": "Miami", "lat": 25.7617, "lon": -80.1918},
            {"name": "亚特兰大", "en": "Atlanta", "lat": 33.7490, "lon": -84.3880},
        ],
    },
    "南部": {
        "states": ["TX", "LA", "MS", "AL"],
        "cities": [
            {"name": "休斯顿", "en": "Houston", "lat": 29.7604, "lon": -95.3698},
            {"name": "新奥尔良", "en": "New Orleans", "lat": 29.9511, "lon": -90.0715},
        ],
    },
    "中部": {
        "states": ["IL", "MO", "KS", "IA", "NE"],
        "cities": [
            {"name": "芝加哥", "en": "Chicago", "lat": 41.8781, "lon": -87.6298},
            {"name": "堪萨斯城", "en": "Kansas City", "lat": 39.0997, "lon": -94.5786},
        ],
    },
    "西部": {
        "states": ["CA", "OR", "WA"],
        "cities": [
            {"name": "洛杉矶", "en": "Los Angeles", "lat": 34.0522, "lon": -118.2437},
            {"name": "旧金山", "en": "San Francisco", "lat": 37.7749, "lon": -122.4194},
        ],
    },
    "西南部": {
        "states": ["AZ", "NM", "NV"],
        "cities": [
            {"name": "凤凰城", "en": "Phoenix", "lat": 33.4484, "lon": -112.0740},
            {"name": "拉斯维加斯", "en": "Las Vegas", "lat": 36.1699, "lon": -115.1398},
        ],
    },
    "西北部": {
        "states": ["WA", "OR", "ID", "MT"],
        "cities": [
            {"name": "西雅图", "en": "Seattle", "lat": 47.6062, "lon": -122.3321},
            {"name": "波特兰", "en": "Portland", "lat": 45.5152, "lon": -122.6784},
        ],
    },
    "中西部山地": {
        "states": ["CO", "UT", "WY"],
        "cities": [
            {"name": "丹佛", "en": "Denver", "lat": 39.7392, "lon": -104.9903},
            {"name": "盐湖城", "en": "Salt Lake City", "lat": 40.7608, "lon": -111.8910},
        ],
    },
}

# 天气状况英文 → 中文翻译
WEATHER_CN = {
    "Sunny": "晴天", "Clear": "晴朗", "Mostly Sunny": "大部晴朗",
    "Mostly Clear": "大部晴朗", "Partly Sunny": "局部多云",
    "Partly Cloudy": "局部多云", "Cloudy": "多云", "Overcast": "阴天",
    "Light Rain": "小雨", "Rain": "雨", "Heavy Rain": "大雨",
    "Rain Showers": "阵雨", "Thunderstorms": "雷暴",
    "Severe Thunderstorms": "强雷暴", "Snow": "雪", "Light Snow": "小雪",
    "Heavy Snow": "大雪", "Blizzard": "暴风雪", "Sleet": "雨夹雪",
    "Freezing Rain": "冻雨", "Fog": "雾", "Haze": "霾",
    "Windy": "大风", "Breezy": "微风", "Hot": "炎热",
    "Cold": "寒冷", "Fair": "晴好",
}

# NWS 预警类型英文 → 中文
ALERT_CN = {
    "Tornado Warning": "龙卷风警告",
    "Tornado Watch": "龙卷风警戒",
    "Severe Thunderstorm Warning": "强雷暴警告",
    "Severe Thunderstorm Watch": "强雷暴警戒",
    "Flash Flood Warning": "山洪警告",
    "Flash Flood Watch": "山洪警戒",
    "Flood Warning": "洪水警告",
    "Flood Watch": "洪水警戒",
    "Flood Advisory": "洪水预警",
    "Hurricane Warning": "飓风警告",
    "Hurricane Watch": "飓风警戒",
    "Tropical Storm Warning": "热带风暴警告",
    "Tropical Storm Watch": "热带风暴警戒",
    "Winter Storm Warning": "冬季风暴警告",
    "Winter Storm Watch": "冬季风暴警戒",
    "Blizzard Warning": "暴风雪警告",
    "Ice Storm Warning": "冰暴警告",
    "Heavy Snow Warning": "大雪警告",
    "Freeze Warning": "霜冻警告",
    "Frost Advisory": "霜冻预警",
    "Wind Chill Warning": "寒潮警告",
    "Wind Chill Advisory": "寒潮预警",
    "Heat Advisory": "高温预警",
    "Excessive Heat Warning": "极端高温警告",
    "Excessive Heat Watch": "极端高温警戒",
    "Red Flag Warning": "火灾危险警告",
    "Fire Weather Watch": "火灾天气警戒",
    "High Wind Warning": "大风警告",
    "Wind Advisory": "大风预警",
    "Dense Fog Advisory": "浓雾预警",
    "Dust Storm Warning": "沙尘暴警告",
    "Severe Weather Statement": "恶劣天气通报",
    "Special Weather Statement": "特殊天气通报",
    "Coastal Flood Advisory": "沿海洪水预警",
    "Coastal Flood Warning": "沿海洪水警告",
    "Rip Current Statement": "离岸流预警",
    "Air Quality Alert": "空气质量预警",
    "Hard Freeze Warning": "严重霜冻警告",
    "Freeze Watch": "霜冻警戒",
}

# 预警严重等级中文
SEVERITY_CN = {
    "Extreme": "极端",
    "Severe": "严重",
    "Moderate": "中等",
    "Minor": "轻微",
    "Unknown": "未知",
}

# 只推送 Moderate 及以上级别的预警
MIN_SEVERITY = "Moderate"

# 预报天数（NWS 最多 7 天）
FORECAST_DAYS = 7

# 所有涉及州（用于全局极端天气扫描）
ALL_STATES = []
for _r in REGIONS.values():
    for _s in _r["states"]:
        if _s not in ALL_STATES:
            ALL_STATES.append(_s)
