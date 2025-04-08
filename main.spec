# -*- mode: python ; coding: utf-8 -*-

import os
import subprocess
import shutil
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

def verify_and_copy_devcon():
    try:
        completed = subprocess.run(["where", "devcon"], capture_output=True, text=True, check=True)
        devcon_path = os.path.abspath(completed.stdout.strip().splitlines()[0])
        target_path = os.path.abspath(os.path.join(os.getcwd(), "devcon.exe"))

        if os.path.samefile(devcon_path, target_path):
            print(f"devcon.exe already present in project folder: {target_path}")
        else:
            shutil.copy2(devcon_path, target_path)
            print(f"devcon.exe copied from {devcon_path} to {target_path}")
    except subprocess.CalledProcessError:
        print("'devcon.exe' not found on the system. Make sure it is installed and added to the PATH.")
        print("Devcon installation instructions: https://learn.microsoft.com/en-us/windows-hardware/drivers/devtest/devcon")
        input("Press Enter to continue...")



verify_and_copy_devcon()

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('images/*.png', 'images'), ('images/*.ico', 'images'), ('devcon.exe', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='MCG app',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    icon='images/Icon.ico',
    uac_admin=True
)
