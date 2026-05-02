$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$root = Split-Path -Parent $PSScriptRoot
$mcpDir = Join-Path $root "mcp"

function Start-WorkflowCommand {
    param(
        [string]$Command
    )
    Start-Process powershell -ArgumentList @(
        "-NoExit",
        "-Command",
        "Set-Location -LiteralPath '$mcpDir'; $Command"
    ) | Out-Null
}

$form = New-Object System.Windows.Forms.Form
$form.Text = "Notion 脚本操作面板（本地兜底）"
$form.Size = New-Object System.Drawing.Size(520, 480)
$form.StartPosition = "CenterScreen"
$form.TopMost = $true

$title = New-Object System.Windows.Forms.Label
$title.Text = "Notion 本地脚本 GUI（插件不可用时使用）"
$title.AutoSize = $true
$title.Location = New-Object System.Drawing.Point(20, 20)
$title.Font = New-Object System.Drawing.Font("Microsoft YaHei UI", 11, [System.Drawing.FontStyle]::Bold)
$form.Controls.Add($title)

$desc = New-Object System.Windows.Forms.Label
$desc.Text = "建议默认走插件通道；这里是脚本兜底操作。"
$desc.AutoSize = $true
$desc.Location = New-Object System.Drawing.Point(20, 55)
$form.Controls.Add($desc)

function Add-MenuButton {
    param(
        [string]$Text,
        [int]$Y,
        [scriptblock]$OnClick
    )
    $btn = New-Object System.Windows.Forms.Button
    $btn.Text = $Text
    $btn.Size = New-Object System.Drawing.Size(460, 36)
    $btn.Location = New-Object System.Drawing.Point(20, $Y)
    $btn.Add_Click($OnClick)
    $form.Controls.Add($btn)
}

Add-MenuButton -Text "CRUD 向导（notion_write_menu）" -Y 95 -OnClick {
    Start-WorkflowCommand "python '.\notion_write_menu.py'"
    $form.Close()
}

Add-MenuButton -Text "同步（Interactive）" -Y 140 -OnClick {
    Start-WorkflowCommand "python '.\run_notion_workflow.py' --config '.\notion_workflow.sync.json' --interactive"
    $form.Close()
}

Add-MenuButton -Text "读取（Interactive）" -Y 185 -OnClick {
    Start-WorkflowCommand "python '.\run_notion_workflow.py' --config '.\notion_workflow.read.json' --interactive"
    $form.Close()
}

Add-MenuButton -Text "Drill Read（只读验证）" -Y 230 -OnClick {
    Start-WorkflowCommand ".\drill-read.cmd"
    $form.Close()
}

Add-MenuButton -Text "Drill Create（Dry-Run）" -Y 275 -OnClick {
    Start-WorkflowCommand ".\drill-create.cmd"
    $form.Close()
}

Add-MenuButton -Text "Drill Update（Dry-Run）" -Y 320 -OnClick {
    Start-WorkflowCommand ".\drill-update.cmd"
    $form.Close()
}

Add-MenuButton -Text "打开 .cursor\\mcp 目录" -Y 365 -OnClick {
    Start-Process explorer.exe $mcpDir | Out-Null
    $form.Close()
}

[void]$form.ShowDialog()
