# Run this as Administrator
$taskName = "Graph Viewer App Manager"
$scriptPath = "C:\GitRepos\GraphViewerApp\run.ps1"

$action = New-ScheduledTaskAction -Execute "pwsh.exe" -Argument "-ExecutionPolicy Bypass -File `"$scriptPath`""
$trigger = New-ScheduledTaskTrigger -AtStartup
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal

Write-Host "Task created successfully! Your Graph Viewer App will now start automatically with Windows." -ForegroundColor Green