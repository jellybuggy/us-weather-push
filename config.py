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

# 预报天数（NWS 最多 7 天）
FORECAST_DAYS = 7
