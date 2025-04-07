Set objShell = CreateObject("WScript.Shell")
strFilePath = "eula.txt"

x=msgbox("Attempting Minecraft autoconfiguration" & vbNewLine & "DO NOT TOUCH YOUR PC DURING THIS PART!",0+48+4096,"Minecraft Manager Installer")

objShell.Run "notepad.exe " & strFilePath, 1, False
WScript.Sleep 1000
objShell.SendKeys "^{END}"
objShell.SendKeys "{BS}"
objShell.SendKeys "{BS}"
objShell.SendKeys "{BS}"
objShell.SendKeys "{BS}"
objShell.SendKeys "{BS}"
objShell.SendKeys "{BS}"
objShell.SendKeys "true"
objShell.SendKeys "^s"
objShell.SendKeys "%{F4}"

x=msgbox("Minecraft autoconfiguration done!",0+64,"Minecraft Manager Installer")