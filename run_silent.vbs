Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")
strDir = FSO.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = strDir

' Check if isolated virtual environment exists
If FSO.FileExists(strDir & "\.venv\Scripts\pythonw.exe") Then
    WshShell.Run """" & strDir & "\.venv\Scripts\pythonw.exe"" """ & strDir & "\main.pyw""", 0, False
Else
    WshShell.Run "cmd.exe /c """ & strDir & "\run.bat""", 1, True
End If
