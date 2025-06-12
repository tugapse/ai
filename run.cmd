@ECHO OFF

SET folder=%~dp0%

setlocal
set PYTHONPATH=%folder%
python "%folder%/init.py" %*
endlocal