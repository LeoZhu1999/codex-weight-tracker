Option Explicit

Dim shell, fso, scriptDir, pluginRoot, logFile, command
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
pluginRoot = fso.GetParentFolderName(scriptDir)
logFile = shell.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\CodexWeightTracker\dashboard.log"

If shell.Run("cmd.exe /c where uv >nul 2>nul", 0, True) <> 0 Then
  MsgBox "The required command 'uv' was not found. Re-run the Codex Weight Tracker installer.", vbExclamation, "Codex Weight Tracker"
  WScript.Quit 1
End If

command = "cmd.exe /c " & Q("uv run --project " & Q(pluginRoot) & " --frozen python -m weight_tracker.cli chart >> " & Q(logFile) & " 2>&1")
shell.Run command, 0, False

Function Q(value)
  Q = Chr(34) & Replace(value, Chr(34), Chr(34) & Chr(34)) & Chr(34)
End Function
