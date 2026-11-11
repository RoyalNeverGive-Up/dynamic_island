Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")
strDir = FSO.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = strDir

' 检查独立虚拟环境是否存在
If FSO.FileExists(strDir & "\.venv\Scripts\pythonw.exe") Then
    ' 虚拟环境已就绪，完全静默启动灵动岛
    WshShell.Run """" & strDir & "\.venv\Scripts\pythonw.exe"" """ & strDir & "\main.pyw""", 0, False
Else
    ' 首次启动尚未配置虚拟环境，调起 run.bat 引导安装
    WshShell.Run "cmd.exe /c """ & strDir & "\run.bat""", 1, True
End If
