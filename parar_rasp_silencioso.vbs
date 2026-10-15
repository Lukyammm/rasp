' ===================================================
' RASP - Finalizador Silencioso (Fecha os servidores)
' ===================================================
Option Explicit

Dim WshShell, FSO, scriptDir

Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")

scriptDir = FSO.GetParentFolderName(WScript.ScriptFullName)

On Error Resume Next
WshShell.Run "powershell -ExecutionPolicy Bypass -File """ & scriptDir & "\kill_ports.ps1""", 0, True
On Error GoTo 0
