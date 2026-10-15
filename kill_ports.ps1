# Encerra os processos que escutam nas portas do RASP (8000 = API, 8080 = interface)
Get-NetTCPConnection -LocalPort 8000,8080 -State Listen -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty OwningProcess -Unique |
    Where-Object { $_ -gt 4 } |
    ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }
