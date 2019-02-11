@echo off
setlocal
set PythonExe=
set PythonExeFlags=

REM "loop to find the full path for python executable file"
for %%i in (cmd bat exe) do (
    for %%j in (python.%%i) do (
        call :SetPythonExe "%%~$PATH:j"
    )
)

REM "sets the python path using ftype command"
for /f "tokens=2 delims==" %%i in ('assoc .py') do (
    for /f "tokens=2 delims==" %%j in ('ftype %%i') do (
        for /f "tokens=1" %%k in ("%%j") do (
            call :SetPythonExe %%k
        )
    )
)
REM "Run rdk file using python"
"%PythonExe%" %PythonExeFlags% "%~dpn0" %*
goto :EOF

REM "Subroutine for setting python executables path to PythonExe variable"
:SetPythonExe
if not [%1]==[""] (
    if ["%PythonExe%"]==[""] (
        set PythonExe=%~1
    )
)
goto :EOF