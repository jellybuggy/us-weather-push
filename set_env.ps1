# 美德公假提醒 - 环境变量配置脚本
# 运行方式: .\set_env.ps1
# 或: powershell -File set_env.ps1

$env:EMAIL_SMTP = "smtp.hxpmold.com"
$env:EMAIL_PORT = "465"
$env:EMAIL_SENDER = "info@hxpmold.com"
$env:EMAIL_PASSWORD = "Mimashi369.com"
$env:EMAIL_RECEIVER = "service@hxpmold.com"

Write-Host "环境变量已设置（仅当前会话）" -ForegroundColor Green
Write-Host "运行: uv run --with holidays --with win11toast python holiday.py"
