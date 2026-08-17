Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Pega a pasta onde este arquivo VBS esta salvo
strPath = fso.GetParentFolderName(WScript.ScriptFullName)

' Define a pasta do projeto como diretorio de trabalho
WshShell.CurrentDirectory = strPath

' Executa o bat silenciosamente
WshShell.Run "cmd /c ""iniciar_central.bat""", 0, False

Set WshShell = Nothing
Set fso = Nothing