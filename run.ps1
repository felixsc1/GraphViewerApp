# Keeps the Graph Viewer Streamlit app running and appends its console
# output (stdout and stderr) to app_log.txt for the whole process lifetime.
# Streamlit, the venv, and this script live at the same path on every machine.

$ErrorActionPreference = "Stop"

if (-not ("StreamlitProcessJob" -as [type])) {
    Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;

public static class StreamlitProcessJob {
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode)]
    static extern IntPtr CreateJobObject(IntPtr lpJobAttributes, string lpName);

    [DllImport("kernel32.dll")]
    static extern bool SetInformationJobObject(IntPtr hJob, int infoType, IntPtr lpJobObjectInfo, uint cbJobObjectInfoLength);

    [DllImport("kernel32.dll")]
    static extern bool AssignProcessToJobObject(IntPtr hJob, IntPtr hProcess);

    const int JobObjectExtendedLimitInformation = 9;
    const uint JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000;

    static IntPtr jobHandle = IntPtr.Zero;

    public static bool Track(IntPtr processHandle) {
        if (jobHandle == IntPtr.Zero) {
            jobHandle = CreateJobObject(IntPtr.Zero, null);
            var basic = new JOBOBJECT_BASIC_LIMIT_INFORMATION();
            basic.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
            var extended = new JOBOBJECT_EXTENDED_LIMIT_INFORMATION();
            extended.BasicLimitInformation = basic;
            int length = Marshal.SizeOf(typeof(JOBOBJECT_EXTENDED_LIMIT_INFORMATION));
            IntPtr pointer = Marshal.AllocHGlobal(length);
            try {
                Marshal.StructureToPtr(extended, pointer, false);
                if (!SetInformationJobObject(jobHandle, JobObjectExtendedLimitInformation, pointer, (uint)length)) {
                    return false;
                }
            } finally {
                Marshal.FreeHGlobal(pointer);
            }
        }
        return AssignProcessToJobObject(jobHandle, processHandle);
    }

    [StructLayout(LayoutKind.Sequential)]
    struct JOBOBJECT_BASIC_LIMIT_INFORMATION {
        public long PerProcessUserTimeLimit;
        public long PerJobUserTimeLimit;
        public uint LimitFlags;
        public UIntPtr MinimumWorkingSetSize;
        public UIntPtr MaximumWorkingSetSize;
        public uint ActiveProcessLimit;
        public IntPtr Affinity;
        public uint PriorityClass;
        public uint SchedulingClass;
    }

    [StructLayout(LayoutKind.Sequential)]
    struct IO_COUNTERS {
        public ulong ReadOperationCount;
        public ulong WriteOperationCount;
        public ulong OtherOperationCount;
        public ulong ReadTransferCount;
        public ulong WriteTransferCount;
        public ulong OtherTransferCount;
    }

    [StructLayout(LayoutKind.Sequential)]
    struct JOBOBJECT_EXTENDED_LIMIT_INFORMATION {
        public JOBOBJECT_BASIC_LIMIT_INFORMATION BasicLimitInformation;
        public IO_COUNTERS IoInfo;
        public UIntPtr ProcessMemoryLimit;
        public UIntPtr JobMemoryLimit;
        public UIntPtr PeakProcessMemoryUsed;
        public UIntPtr PeakJobMemoryUsed;
    }
}
"@
}

$applicationPath = "C:\GitRepos\GraphViewerApp\app.py"
$pythonExe = "C:\GitRepos\GraphViewerApp\venv\Scripts\python.exe"
$workingDirectory = "C:\GitRepos\GraphViewerApp"
$logFile = "C:\GitRepos\GraphViewerApp\app_log.txt"

function Write-Console {
    param(
        [string]$Message,
        [ConsoleColor]$Color
    )
    try {
        if ($PSBoundParameters.ContainsKey("Color")) {
            Write-Host $Message -ForegroundColor $Color
        } else {
            Write-Host $Message
        }
    } catch {
    }
}

function Write-LogLine {
    param([string]$Line)
    # Open and close per line so the log can be read while this script is running.
    # UTF-16 matches the encoding Windows PowerShell used for the original log.
    $stream = New-Object System.IO.FileStream(
        $logFile,
        [System.IO.FileMode]::Append,
        [System.IO.FileAccess]::Write,
        [System.IO.FileShare]::ReadWrite)
    $writer = New-Object System.IO.StreamWriter($stream, [System.Text.Encoding]::Unicode)
    try {
        $writer.WriteLine($Line)
    } finally {
        $writer.Dispose()
    }
    # Task Scheduler on Server 2019 has no console. A failed host write must not
    # abort logging or look like a Streamlit failure.
    Write-Console $Line
}

function Repair-LogEncoding {
    if (-not (Test-Path -LiteralPath $logFile)) {
        return
    }

    $bytes = [System.IO.File]::ReadAllBytes($logFile)
    if ($bytes.Length -eq 0) {
        return
    }

    $isUtf16 = ($bytes.Length -ge 2 -and $bytes[0] -eq 255 -and $bytes[1] -eq 254)
    if ($isUtf16) {
        return
    }

    $utf8 = New-Object System.Text.UTF8Encoding $true
    $text = [System.IO.File]::ReadAllText($logFile, $utf8)
    [System.IO.File]::WriteAllText($logFile, $text, [System.Text.Encoding]::Unicode)
}

function Test-SupervisorCancelled {
    param($ErrorRecord)
    $exception = $ErrorRecord.Exception
    while ($null -ne $exception) {
        if ($exception -is [System.Management.Automation.PipelineStoppedException] -or
            $exception -is [System.OperationCanceledException]) {
            return $true
        }
        $exception = $exception.InnerException
    }
    return $false
}

function Stop-OwnedStreamlit {
    $process = $script:StreamlitProcess
    $script:StreamlitProcess = $null
    $stoppedIds = New-Object System.Collections.Generic.List[int]

    if ($null -ne $process) {
        try {
            if (-not $process.HasExited) {
                & "$env:SystemRoot\System32\taskkill.exe" /PID $process.Id /T /F *> $null
                $stoppedIds.Add([int]$process.Id)
            }
        } catch {
        }
        try {
            $process.Dispose()
        } catch {
        }
    }

    foreach ($existing in @(Get-ManagedStreamlitProcesses)) {
        & "$env:SystemRoot\System32\taskkill.exe" /PID $existing.ProcessId /T /F *> $null
        if (-not $stoppedIds.Contains([int]$existing.ProcessId)) {
            $stoppedIds.Add([int]$existing.ProcessId)
        }
    }

    if ($stoppedIds.Count -gt 0) {
        $idList = $stoppedIds -join ", "
        Write-LogLine "Stopped Streamlit because the supervisor exited at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') (pid $idList)"
    }
}

function Get-ManagedStreamlitProcesses {
    Get-CimInstance Win32_Process | Where-Object {
        $_.CommandLine -and
        ($_.CommandLine -like "*streamlit*") -and
        ($_.CommandLine -like "*$applicationPath*")
    }
}

function Consume-StreamLine {
    param(
        $Task,
        [ref]$StreamOpen,
        [ref]$NextTask,
        $Reader
    )

    if (-not $StreamOpen.Value -or -not $Task.IsCompleted) {
        return $false
    }

    $line = $null
    $faulted = $false
    try {
        $line = $Task.Result
    } catch {
        $faulted = $true
    }

    if ($faulted -or $null -eq $line) {
        $StreamOpen.Value = $false
        return $true
    }

    Write-LogLine $line
    if (-not $script:SawReady -and $line -match "You can now view") {
        $script:SawReady = $true
        Write-Console "Application started successfully!" Green
    }

    $NextTask.Value = $Reader.ReadLineAsync()
    return $true
}

function Start-ManagedStreamlit {
    if (-not (Test-Path -LiteralPath $pythonExe)) {
        throw "Python executable not found: $pythonExe"
    }
    if (-not (Test-Path -LiteralPath $applicationPath)) {
        throw "Application not found: $applicationPath"
    }

    $utf8 = New-Object System.Text.UTF8Encoding $false
    $script:SawReady = $false

    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $pythonExe
    # -u and PYTHONUNBUFFERED keep Python from block-buffering pipe output.
    $psi.Arguments = "-u -m streamlit run `"$applicationPath`" --server.port 8080"
    $psi.WorkingDirectory = $workingDirectory
    $psi.UseShellExecute = $false
    $psi.RedirectStandardInput = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.CreateNoWindow = $true
    $psi.EnvironmentVariables["PYTHONUNBUFFERED"] = "1"
    $psi.EnvironmentVariables["PYTHONIOENCODING"] = "utf-8"
    # Hides "You can now view your Streamlit app...", the URL lines, and the skills note.
    $psi.EnvironmentVariables["STREAMLIT_LOGGER_HIDE_WELCOME_MESSAGE"] = "true"
    # First launch on a new machine asks for an email. Skip that prompt.
    $psi.EnvironmentVariables["STREAMLIT_SERVER_SHOW_EMAIL_PROMPT"] = "false"
    $outputEncoding = $psi.GetType().GetProperty("StandardOutputEncoding")
    if ($null -ne $outputEncoding) {
        $outputEncoding.SetValue($psi, $utf8, $null)
        $psi.GetType().GetProperty("StandardErrorEncoding").SetValue($psi, $utf8, $null)
    }

    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $psi
    [void]$process.Start()
    $script:StreamlitProcess = $process
    try {
        if (-not [StreamlitProcessJob]::Track($process.Handle)) {
            Write-LogLine "Could not tie Streamlit to this supervisor. Ctrl+C will still try to stop it."
        }
    } catch {
        Write-LogLine "Could not tie Streamlit to this supervisor: $($_.Exception.Message)"
    }

    $stdoutReader = $process.StandardOutput
    $stderrReader = $process.StandardError

    Write-Console "Starting application (pid $($process.Id))..."
    Write-LogLine "Application started at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') (pid $($process.Id))"

    $sentEnter = $false
    $startedAt = Get-Date
    $exitedAt = $null
    $stdoutOpen = $true
    $stderrOpen = $true
    $stdoutTask = $stdoutReader.ReadLineAsync()
    $stderrTask = $stderrReader.ReadLineAsync()

    while ($stdoutOpen -or $stderrOpen -or -not $process.HasExited) {
        try {
            if (-not $sentEnter -and (((Get-Date) - $startedAt).TotalSeconds -ge 2)) {
                try {
                    $process.StandardInput.WriteLine("")
                } catch {
                    Write-LogLine "Could not write to Streamlit stdin: $($_.Exception.Message)"
                }
                $sentEnter = $true
            }

            $progress = $false
            if (Consume-StreamLine $stdoutTask ([ref]$stdoutOpen) ([ref]$stdoutTask) $stdoutReader) {
                $progress = $true
            }
            if (Consume-StreamLine $stderrTask ([ref]$stderrOpen) ([ref]$stderrTask) $stderrReader) {
                $progress = $true
            }

            if ($process.HasExited) {
                if ($null -eq $exitedAt) {
                    $exitedAt = Get-Date
                }
                if (((Get-Date) - $exitedAt).TotalSeconds -gt 5) {
                    break
                }
            }

            if (-not $progress) {
                Start-Sleep -Milliseconds 100
            }
        } catch {
            if (Test-SupervisorCancelled $_) {
                throw
            }
            $stillRunning = $false
            try {
                $stillRunning = -not $process.HasExited
            } catch {
                $stillRunning = $false
            }
            if (-not $stillRunning) {
                break
            }
            Start-Sleep -Milliseconds 200
        }
    }

    try {
        $process.WaitForExit()
        $exitCode = $process.ExitCode
    } catch {
        $exitCode = -1
    }
    $script:StreamlitProcess = $null
    Write-LogLine "Application exited at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') with code $exitCode"
    Write-Console "Application exited with code $exitCode" Yellow
    $process.Dispose()
}

Repair-LogEncoding
Write-Console "Graph Viewer supervisor running. Log: $logFile"

$announcedExisting = $false
try {
    while ($true) {
        try {
            $running = @(Get-ManagedStreamlitProcesses)
            if ($running.Count -gt 0) {
                $ids = ($running | ForEach-Object { $_.ProcessId }) -join ", "
                if (-not $announcedExisting) {
                    Write-LogLine "Streamlit for this app is already running (pid $ids). Waiting for it to exit before starting a logged instance. $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
                    Write-Console "Application already running (pid $ids). Waiting..."
                    $announcedExisting = $true
                }
                Start-Sleep -Seconds 30
                continue
            }

            $announcedExisting = $false
            Start-ManagedStreamlit
            Start-Sleep -Seconds 5
        } catch {
            if (Test-SupervisorCancelled $_) {
                throw
            }
            $message = "Error occurred at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss'): $($_.Exception.Message)"
            Write-LogLine $message
            Write-Console $message Red
            Start-Sleep -Seconds 60
        }
    }
} finally {
    Stop-OwnedStreamlit
}
