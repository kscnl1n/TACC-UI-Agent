
# This file was not originally present - I run Windows on my laptop at home, so I added it to test whether this
# pipeline would work on Windows before uploading to Github. Large parts of it are commented out because they created
# debug logs that might be useful if you run into problems with with windows bash file but would otherwise bloat the folder
# with unnecessary files.

# Keep in mind that environment variable installations may differ from Linux (what the HPC system this was run on)to Windows.



param(
  [string]$Prompt = "Turn these input files into a website dashboard."
)

$ErrorActionPreference = "Stop"


# $shellContext = [ordered]@{
#   sessionId = "c9d150"
#   runId = "windows-pre-fix"
#   hypothesisId = "W1_W2_W3"
#   location = "run.ps1:12"
#   message = "PowerShell runtime context"
#   data = @{
#     pwd = (Get-Location).Path
#     psEdition = $PSVersionTable.PSEdition
#     psVersion = $PSVersionTable.PSVersion.ToString()
#     path = $env:PATH
#   }
#   timestamp = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
# }
# $shellContext | ConvertTo-Json -Compress | Add-Content -Path "debug-c9d150.log"


$candidates = @("py -3", "python", "python3", "C:\Python313\python.exe")
$pythonCmd = $null

foreach ($candidate in $candidates) {
  try {
    if ($candidate -eq "py -3") {
      py -3 -c "import langchain_core,langchain_ollama,pandas" *> $null
    } else {
      & $candidate -c "import langchain_core,langchain_ollama,pandas" *> $null
    }
    if ($LASTEXITCODE -eq 0) {
      $pythonCmd = $candidate
      break
    }
  } catch {
    continue
  }
}

# $selectionLog = [ordered]@{
#   sessionId = "c9d150"
#   runId = "windows-post-fix"
#   hypothesisId = "W1_W2_W3"
#   location = "run.ps1:43"
#   message = "Selected python candidate"
#   data = @{
#     pythonCmd = $(if ($pythonCmd) { $pythonCmd } else { "missing" })
#   }
#   timestamp = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
# }
# $selectionLog | ConvertTo-Json -Compress | Add-Content -Path "debug-c9d150.log"


if (-not $pythonCmd) {
  # $errorLog = [ordered]@{
  #   sessionId = "c9d150"
  #   runId = "windows-post-fix"
  #   hypothesisId = "W1_W2_W3"
  #   location = "run.ps1:58"
  #   message = "No interpreter with required modules found"
  #   data = @{
  #     hint = "Use py -3 -m pip install -r requirements.txt"
  #   }
  #   timestamp = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
  # }
  # $errorLog | ConvertTo-Json -Compress | Add-Content -Path "debug-c9d150.log"
  throw "No Python interpreter with required modules found. Try: py -3 -m pip install -r requirements.txt"
}

if ($pythonCmd -eq "py -3") {
  py -3 agent.py --prompt "$Prompt"
} else {
  & $pythonCmd agent.py --prompt "$Prompt"
}
