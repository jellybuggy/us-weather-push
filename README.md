# 50-Day Winter Replenishment Alert System

基于官方天气趋势、NWS短期预警、CPC中长期趋势和市场新闻信号，提前50天辅助 Outdoor Faucet Cover 的生产、海运、FBA补货和Amazon广告决策。

## 系统架构

本系统包含两个模块，同时运行：

### Module 1: Daily Weather Forecast
每日天气预报推送
- 美国重点州/城市的 7 天天气预报
- 最低温度 / 最高温度
- 是否接近或低于 32°F（冰点）
- 降雪、冰冻、暴风雪、寒潮等天气信号
- NWS Active Alerts 实时预警
- 数据来源: NWS API (api.weather.gov)

### Module 2: 50-Day Winter Replenishment Alert
冬季补货决策辅助系统
- Executive Summary - 冬季补货风险等级
- 50-Day Replenishment Risk - 长期趋势判断
- 45-Day Shipping Decision - 海运/FBA发货提醒
- 30-Day Market Watch - 新闻和市场信号监测
- 14-Day Weather Risk - NOAA CPC 展望
- 7-Day Official Alerts - NWS 活跃预警
- 7-Day Daily Weather Forecast - 各城市 7 天预报
- Suggested Amazon Actions - Amazon 操作建议

## 极寒/极热阈值

- **极寒**：< 14°F（-10°C）→ 水龙头保护罩需求暴涨
- **极热**：> 90°F（32°C）→ 水龙头保护罩（防晒）+ 通风口导流罩（冷气）需求上升

## 覆盖区域

| 区域 | 城市 | 州 |
|------|------|-----|
| 东北部 | 纽约、波士顿、水牛城、费城 | NY, MA, PA |
| 中西部 | 芝加哥、底特律、明尼阿波利斯 | IL, MI, MN |
| 山区 | 丹佛、盐湖城 | CO, UT |
| 西北部 | 西雅图、波特兰 | WA, OR |
| 西部 | 洛杉矶 | CA |
| 西南部 | 凤凰城、拉斯维加斯 | AZ, NV |
| 东南部 | 亚特兰大、迈阿密 | GA, FL |
| 南部 | 休斯顿、达拉斯 | TX |

## 硬性规则

- ❌ 不允许编造 30 天、50 天、90 天具体温度
- ❌ 不允许编造极寒概率
- ⚠️ CPC 长期数据只能表达 below normal / near normal / above normal 趋势
- ⚠️ 新闻/RSS 只能作为 media signal / market signal，不能作为官方预警
- ✅ 每个结论必须注明来源
- ✅ 没有可靠数据时写"暂无可靠数据"

## 3 步开始使用

### 第 1 步：Fork 本仓库

点击本页面右上角 **Fork** 按钮，把代码复制到你自己的 GitHub 账号下。

### 第 2 步：开启 QQ 邮箱 SMTP 服务

1. 电脑浏览器打开 [QQ 邮箱](https://mail.qq.com) 并登录
2. 点顶部「设置」→「账户」
3. 往下翻，找到 **IMAP/SMTP 服务**，点「开启」
4. 按提示用手机发短信验证
5. 验证通过后会得到一个 **16 位授权码**（只显示一次，记好）

### 第 3 步：配置 Secrets

在你 Fork 的仓库页面：

1. 点 **Settings**（设置）
2. 左侧找 **Secrets and variables** → **Actions**
3. 点 **New repository secret**，逐个添加以下 5 个：

| Name | Value（填什么） | 示例 |
|------|-----------------|------|
| `EMAIL_SMTP` | 固定填 | `smtp.qq.com` |
| `EMAIL_PORT` | 固定填 | `465` |
| `EMAIL_SENDER` | 你的 QQ 邮箱 | `123456789@qq.com` |
| `EMAIL_PASSWORD` | 第 2 步获取的授权码 | `abcdefghijklmnop` |
| `EMAIL_RECEIVER` | 接收邮件的邮箱 | `123456789@qq.com` |

### 完成！

- **自动**：每天北京时间 7:30 自动推送（Module 1 + Module 2）
- **手动**：仓库页面 → **Actions** → **50-Day Winter Replenishment Alert System** → **Run workflow**

## 邮件结构说明

### Module 1: Daily Weather Forecast 邮件标题
