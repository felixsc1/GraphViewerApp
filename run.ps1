$applicationPath = "C:\GitRepos\GraphViewerApp\app.py"
$streamlitModule = "C:\GitRepos\GraphViewerApp\venv\Scripts\streamlit.exe"
$uniqueIdentifier = "*streamlit*run*$applicationPath*"
$logFile = "C:\GitRepos\GraphViewerApp\app_log.txt"

while ($true) {
    # Use Get-WmiObject to check if a specific Streamlit application is running
    $running = Get-WmiObject Win32_Process | Where-Object { $_.CommandLine -like $uniqueIdentifier }
    if (-not $running) {
        Write-Host "Starting application..."
        # Redirecting both standard output and error output to the log file, and specifying server port 80
        & $streamlitModule run $applicationPath --server.port 80 *>> $logFile 2>&1
        "Application restarted at $(Get-Date)" | Out-File -FilePath $logFile -Append
    }
    Start-Sleep -Seconds 30
}
