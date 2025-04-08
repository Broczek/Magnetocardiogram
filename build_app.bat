@echo off
title Universal MCG app Build

echo =======================================
echo Checking for devcon.exe in system...
echo =======================================

where devcon >nul 2>&1
if errorlevel 1 (
    echo 'devcon.exe' not found in PATH.
    echo Please install it or ensure it's available via Windows Driver Kit
    echo https://learn.microsoft.com/en-us/windows-hardware/drivers/devtest/devcon
    pause
    exit /b 1
)
echo devcon.exe found. Continuing...

echo =======================================
echo Locating all python.exe instances...
echo =======================================

set "CONDA_FOUND="
set "FALLBACK_CONDA_PATH=C:\Anaconda\python.exe"

where python > temp_python_paths.txt 2>nul
if errorlevel 1 (
    echo Python interpreter not found. Ensure it's in your PATH.
    pause
    exit /b 1
)

for /f "usebackq delims=" %%P in (temp_python_paths.txt) do (
    echo Checking: %%P
    echo %%P | findstr /i "Anaconda" >nul
    if not errorlevel 1 (
        set "CONDA_FOUND=%%P"
        goto USE_CONDA
    )
)
del temp_python_paths.txt

if exist "%FALLBACK_CONDA_PATH%" (
    echo Manually detected Conda Python at: %FALLBACK_CONDA_PATH%
    set "CONDA_FOUND=%FALLBACK_CONDA_PATH%"
    goto USE_CONDA
)

echo No Anaconda-based Python found — assuming plain Python.
goto USE_PLAIN

:USE_CONDA
echo Anaconda-based Python found: %CONDA_FOUND%

echo Checking if environment 'mkg_build_env' already exists...
call C:\Anaconda\Scripts\conda.exe env list | findstr /i "mkg_build_env" >nul
if %errorlevel%==0 (
    echo Environment 'mkg_build_env' already exists. Removing it first...
    call C:\Anaconda\Scripts\conda.exe remove -y -n mkg_build_env --all
    if errorlevel 1 (
        echo Failed to remove existing environment.
        pause
        exit /b 1
    )
)

echo Creating environment 'mkg_build_env'...
call C:\Anaconda\Scripts\conda.exe create -y -n mkg_build_env python=3.11.11
if errorlevel 1 (
    echo Failed to create conda environment.
    pause
    exit /b 1
)

call C:\Anaconda\Scripts\activate mkg_build_env

echo.
echo Installing dependencies...
pip install -r requirements.txt

echo.
echo Building application...
pyinstaller main.spec
goto END

:USE_PLAIN
echo Installing dependencies...
pip install -r requirements.txt

if errorlevel 1 (
    echo Error during package installation.
    pause
    exit /b 1
)

echo Building application...
pyinstaller main.spec

:END
if errorlevel 1 (
    echo Build failed.
    pause
    exit /b 1
)

echo Done! The .exe file is located in the "dist" folder.
pause