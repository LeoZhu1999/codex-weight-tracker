Option Explicit

Dim shell, fso, scriptDir, pluginRoot, logFile, pythonExe, command
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
pluginRoot = fso.GetParentFolderName(scriptDir)
logFile = shell.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\CodexWeightTracker\dashboard.log"
pythonExe = pluginRoot & "\.venv\Scripts\python.exe"

If fso.FileExists(pythonExe) Then
  command = Q(pythonExe) & " -m weight_tracker.cli chart --log-file " & Q(logFile)
Else
  If shell.Run("cmd.exe /c where uv >nul 2>nul", 0, True) <> 0 Then
    MsgBox "The dashboard runtime was not found. Re-run the Codex Weight Tracker installer.", vbExclamation, "Codex Weight Tracker"
    WScript.Quit 1
  End If
  command = "uv run --project " & Q(pluginRoot) & " --frozen python -m weight_tracker.cli chart --log-file " & Q(logFile)
End If

shell.Run command, 0, False

Function Q(value)
  Q = Chr(34) & Replace(value, Chr(34), Chr(34) & Chr(34)) & Chr(34)
End Function
