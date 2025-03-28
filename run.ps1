$applicationPath = "C:\GitRepos\GraphViewerApp\app.py"
$streamlitModule = "C:\GitRepos\GraphViewerApp\venv\Scripts\streamlit.exe"
$uniqueIdentifier = "*streamlit*run*$applicationPath*"
$logFile = "C:\GitRepos\GraphViewerApp\app_log.txt"

while ($true) {
    # Use Get-WmiObject to check if a specific Streamlit application is running
    $running = Get-WmiObject Win32_Process | Where-Object { $_.CommandLine -like $uniqueIdentifier }
    if (-not $running) {
        Write-Host "Starting application..."
        
        # Start the process with a process object so we can interact with it
        $processStartInfo = New-Object System.Diagnostics.ProcessStartInfo
        $processStartInfo.FileName = $streamlitModule
        $processStartInfo.Arguments = "run $applicationPath --server.port 8080"
        $processStartInfo.UseShellExecute = $false
        $processStartInfo.RedirectStandardInput = $true
        $processStartInfo.RedirectStandardOutput = $true
        $processStartInfo.RedirectStandardError = $true
        $processStartInfo.CreateNoWindow = $false
        
        $process = New-Object System.Diagnostics.Process
        $process.StartInfo = $processStartInfo
        $process.Start() | Out-Null
        
        # Send an empty input (Enter) in case Streamlit asks for email
        Start-Sleep -Seconds 2
        $process.StandardInput.WriteLine("")
        
        # Wait for application to initialize (look for "You can now view" message)
        $outputLine = ""
        $started = $false
        
        # Read output for up to 30 seconds to check for successful startup
        $startTime = Get-Date
        while ((-not $started) -and ((Get-Date) - $startTime).TotalSeconds -lt 30) {
            if (-not $process.StandardOutput.EndOfStream) {
                $outputLine = $process.StandardOutput.ReadLine()
                $outputLine | Out-File -FilePath $logFile -Append
                
                if ($outputLine -match "You can now view") {
                    $started = $true
                    Write-Host "Application started successfully!" -ForegroundColor Green
                    Write-Host $outputLine -ForegroundColor Green
                }
            }
            Start-Sleep -Milliseconds 100
        }
        
        "Application restarted at $(Get-Date)" | Out-File -FilePath $logFile -Append
        
        # Keep the process running - don't wait here as it would block the script
    }
    Start-Sleep -Seconds 30
}
