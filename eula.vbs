Set objShell = CreateObject("WScript.Shell")
strFilePath = "eula.txt"

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