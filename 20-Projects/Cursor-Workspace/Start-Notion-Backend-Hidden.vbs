' 后台启动后端（隐藏控制台窗口）
' 用法：双击本文件，或在 cmd 中执行：
'   wscript "g:\...\20-Projects\Cursor-Workspace\Start-Notion-Backend-Hidden.vbs"

Option Explicit

Dim shell, fso, cmdPath
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

cmdPath = fso.GetParentFolderName(WScript.ScriptFullName) & "\Start-Notion-Backend.cmd"
If Not fso.FileExists(cmdPath) Then
  MsgBox "找不到 Start-Notion-Backend.cmd：" & vbCrLf & cmdPath, vbCritical, "Cursor Workspace"
  WScript.Quit 1
End If

' 0 = 隐藏窗口；False = 不等待进程结束
shell.Run """" & cmdPath & """", 0, False
