Set objShell = CreateObject("WScript.Shell")
strFilePath = WScript.Arguments.Item(0)

objShell.Run "notepad.exe " & strFilePath, 1
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