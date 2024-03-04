$applicationPath = "C:\GitRepos\GraphViewerApp\app.py"
$streamlitModule = "C:\GitRepos\GraphViewerApp\venv\Scripts\streamlit.exe"
$uniqueIdentifier = "*streamlit*run*$applicationPath*"

while ($true) {
    # Use Get-WmiObject to check if a specific Streamlit application is running
    $running = Get-WmiObject Win32_Process | Where-Object { $_.CommandLine -like $uniqueIdentifier }
    if (-not $running) {
        Write-Host "Starting application..."
        & $streamlitModule run $applicationPath
        Write-Host "Application restarted at $(Get-Date)"
    }
    Start-Sleep -Seconds 10
}
