# In Powershell, as Administrator type: powershell -ExecutionPolicy Bypass -File ".\Setup_TaskScheduler.ps1"
$taskName = "Graph Viewer App Manager"
$scriptPath = "C:\GitRepos\GraphViewerApp\run.ps1"

$action = New-ScheduledTaskAction -Execute "pwsh.exe" -Argument "-ExecutionPolicy Bypass -File `"$scriptPath`""
$trigger = New-ScheduledTaskTrigger -AtStartup
$trigger.Delay = 'PT30S'  # Delay by 30 seconds after startup
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType S4U -RunLevel Highest

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal

Write-Host "Task created successfully! Your Graph Viewer App will now start automatically with Windows." -ForegroundColor Green