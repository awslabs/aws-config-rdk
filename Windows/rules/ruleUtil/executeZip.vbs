Set objArgs = WScript.Arguments 
InputFolder = objArgs(0) 
ZipFile = objArgs(1) 
CreateObject("Scripting.FileSystemObject").CreateTextFile(ZipFile, True).Write "PK" & Chr(5) & Chr(6) & String(18, vbNullChar) 
Set objShell = CreateObject("Shell.Application") 
Set source = objShell.NameSpace(InputFolder).Items 
objShell.NameSpace(ZipFile).CopyHere(source) 
wScript.Sleep 2000 
