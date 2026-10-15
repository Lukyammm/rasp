$wscript = New-Object -ComObject WScript.Shell

# Update RASP.lnk on Desktop
$shortcutPath = "C:\Users\_EBMQUINTTO_\Desktop\RASP.lnk"
$shortcut = $wscript.CreateShortcut($shortcutPath)
$shortcut.TargetPath = "C:\Windows\System32\wscript.exe"
$shortcut.Arguments = "`"C:\Users\_EBMQUINTTO_\.gemini\antigravity\scratch\SocialScraper\iniciar_rasp_silencioso.vbs`""
$shortcut.WorkingDirectory = "C:\Users\_EBMQUINTTO_\.gemini\antigravity\scratch\SocialScraper"
$shortcut.WindowStyle = 7
$shortcut.IconLocation = "C:\Users\_EBMQUINTTO_\.gemini\antigravity\scratch\SocialScraper\rasp_icon.ico,0"
$shortcut.Description = "RASP - Monitoramento de Redes Sociais"
$shortcut.Save()

# Create Parar RASP.lnk on Desktop
$stopShortcutPath = "C:\Users\_EBMQUINTTO_\Desktop\Parar RASP.lnk"
$stopShortcut = $wscript.CreateShortcut($stopShortcutPath)
$stopShortcut.TargetPath = "C:\Windows\System32\wscript.exe"
$stopShortcut.Arguments = "`"C:\Users\_EBMQUINTTO_\.gemini\antigravity\scratch\SocialScraper\parar_rasp_silencioso.vbs`""
$stopShortcut.WorkingDirectory = "C:\Users\_EBMQUINTTO_\.gemini\antigravity\scratch\SocialScraper"
$stopShortcut.WindowStyle = 7
$stopShortcut.IconLocation = "C:\Windows\System32\shell32.dll,131"
$stopShortcut.Description = "Parar servidores do RASP"
$stopShortcut.Save()

Write-Host "Shortcuts successfully updated/created!"
