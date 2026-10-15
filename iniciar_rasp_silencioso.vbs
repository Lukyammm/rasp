' ===================================================
' RASP - Inicializador Silencioso (Zero Janelas de CMD)
' ===================================================
Option Explicit

Dim WshShell, FSO, scriptDir, http, attempt, ready

Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")

scriptDir = FSO.GetParentFolderName(WScript.ScriptFullName)

' 1. Encerra instancias antigas (janela oculta, aguarda concluir)
On Error Resume Next
WshShell.Run "powershell -NoProfile -ExecutionPolicy Bypass -File """ & scriptDir & "\kill_ports.ps1""", 0, True
On Error GoTo 0

' 2. Backend (API) e 3. Frontend (UI) - ambos ocultos
WshShell.Run """" & scriptDir & "\iniciar_backend.bat""", 0, False
WshShell.Run """" & scriptDir & "\iniciar_frontend.bat""", 0, False

' 4. Aguarda a API responder (ate ~30s) em vez de um tempo fixo
ready = False
For attempt = 1 To 60
    WScript.Sleep 500
    On Error Resume Next
    Set http = CreateObject("MSXML2.ServerXMLHTTP.6.0")
    http.setTimeouts 1000, 1000, 1000, 1000
    http.Open "GET", "http://127.0.0.1:8000/api/health", False
    http.Send
    If Err.Number = 0 Then
        If http.Status = 200 Then ready = True
    End If
    Err.Clear
    On Error GoTo 0
    If ready Then Exit For
Next

' 5. Abre no Google Chrome
WshShell.Run "cmd /c start chrome ""http://127.0.0.1:8080""", 0, False
