# -*- mode: python ; coding: utf-8 -*-

# This is a PyInstaller spec file. It tells PyInstaller how to build the executable.

block_cipher = None

# The Analysis class is the core of the spec file. It analyzes the main script
# to find all dependencies, modules, and data files.
a = Analysis(
    ['app.py'],  # The main entry point of the application.
    pathex=['.'],  # The path to search for imports (current directory).
    binaries=[],  # A list of any non-Python libraries (.dll, .so) to include.

    # This is a crucial section. It tells PyInstaller to bundle non-Python files
    # into the executable. The format is a list of tuples: (source, destination).
    datas=[
        ('templates', 'templates'),  # Bundle the entire 'templates' folder.
        ('static', 'static'),        # Bundle the entire 'static' folder.
        ('config/config.ini.template', 'config'), # Bundle the config template.
        ('icon.png', '.')            # Bundle the application icon.
    ],

    hiddenimports=[],  # A list of modules that PyInstaller might not find automatically.
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)

# PYZ creates a .pyz archive from all the Python modules found.
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# EXE assembles the final executable file.
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='hwa_dashboard',  # The name of the final executable file.
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # Use UPX for compression if available.
    upx_exclude=[],
    runtime_tmpdir=None,

    # 'console=False' is important for GUI/background applications on Windows.
    # It prevents a black console window from appearing when the app is run.
    console=False,

    icon='icon.png'  # The icon for the executable file itself.
)
