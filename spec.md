# 外贸项目追踪系统 - 规格文档

## 1. 项目概述

**项目名称：** 外贸项目追踪系统（Mold Project Tracker）
**核心功能：** 帮助注塑模具厂追踪项目进度、管理邮件、自动提醒待处理事项
**目标用户：** 工厂管理人员（厂二代）+ 同事

## 2. 工作流程

```
报价 → 确认 → 收模具首款 → 开模 → 样品 → 收模具费余款 → 收产品首款 → 量产 → 发货 → 收尾款
```

**文件夹命名格式（本地）：**
```
[阶段]-[材料]-[产品名]-[客户简称]-[日期]
示例：报价-PA66-壳体-KUNZ-20260526
```

**邮件关键词映射：**
每个项目可配置多个关键词（德语），用于自动匹配客户邮件

## 3. 功能清单

### 3.1 项目管理
- 读取指定文件夹下的所有项目，自动识别阶段
- 支持按阶段、客户、日期筛选
- 每个项目显示：名称、阶段、创建日期、最新更新时间

### 3.2 邮件归类
- 连接阿里云企业邮箱（IMAP）
- 按项目关键词自动匹配邮件
- 邮件显示在对应项目下，按时间排序
- 自动提取价格、数量、材料等关键信息

### 3.3 待确认事项
- 每个项目可添加「待确认问题」
- 记录：问题内容、创建日期、是否等待回复、备注
- 超1天未回复自动触发三种方式提醒

### 3.4 提醒系统
触发提醒时，**同时**发出三种通知：
- **弹窗提醒**：Windows Toast 通知，工作中即时弹窗
- **飞书提醒**：通过飞书 Webhook 推送到手机和同事
- **邮件提醒**：发送邮件到 info@hxpmold.com

### 3.5 讨价还价追踪
- 自动识别邮件中的价格相关词汇（如 "Preis", "Kosten", "€", "USD", "降价", "优惠"）
- 记录每次报价变化，生成简单的价格走势

## 4. 技术方案

### 前端（静态托管）
- **托管**：GitHub Pages（与HSK3项目相同方式）
- **数据**：Firebase Firestore（云端数据库）
- **界面**：纯静态 HTML/CSS/JS

### 后端（邮件同步）
- **语言**：Python
- **邮件**：IMAP（阿里云企业邮箱）
- **数据库**：Firebase Firestore
- **弹窗**：Windows Toast (win10toast)
- **飞书**：Requests 库调用 Webhook API
- **邮件发送**：SMTP（阿里云企业邮箱）

## 5. 文件结构

### 前端（GitHub Pages）
```
https://jellybuggy.github.io/mold-tracker/
```

### 本地（Python后端）
```
D:\claude\外贸项目追踪系统\
├── app.py                 # 主程序（邮件同步+提醒）
├── config.json            # 配置文件
├── requirements.txt       # 依赖列表
└── README.md
```

## 6. Firebase 配置

```javascript
const firebaseConfig = {
  apiKey: "AIzaSyCOv-4T1z5ljOS1aecqcb7QyDE_WMVR5Fw",
  authDomain: "business-tracker-13524.firebaseapp.com",
  projectId: "business-tracker-13524",
  storageBucket: "business-tracker-13524.firebasestorage.app",
  messagingSenderId: "604656795667",
  appId: "1:604656795667:web:034196714a302a5f8f3fe6"
};
```

## 7. 配置项

```json
{
  "email": "info@hxpmold.com",
  "email_password": "YOUR_PASSWORD",
  "imap_server": "imap.mxhichina.com",
  "imap_port": 993,
  "smtp_server": "smtp.mxhichina.com",
  "smtp_port": 465,
  "projects_folder": "D:\\claude\\外贸项目追踪系统",
  "reminder_days": 1,
  "feishu_webhook": "YOUR_FEISHU_WEBHOOK_URL"
}
```