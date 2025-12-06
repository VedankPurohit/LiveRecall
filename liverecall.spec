# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for LiveRecall
Build with: pyinstaller liverecall.spec
"""
import sys
from pathlib import Path

# Detect platform
IS_MACOS = sys.platform == 'darwin'
IS_WINDOWS = sys.platform == 'win32'

# App metadata
APP_NAME = 'LiveRecall'
APP_VERSION = '0.1.0'
APP_BUNDLE_ID = 'com.liverecall.app'

# Paths
ROOT = Path(SPECPATH)
ENTRY_POINT = str(ROOT / 'main.py')
WEB_OUT = str(ROOT / 'web' / 'out')
ICON_MACOS = str(ROOT / 'assets' / 'icon.icns') if (ROOT / 'assets' / 'icon.icns').exists() else None
ICON_WINDOWS = str(ROOT / 'assets' / 'icon.ico') if (ROOT / 'assets' / 'icon.ico').exists() else None

# Find sqlite_vec native library
import sqlite_vec
SQLITE_VEC_DIR = str(Path(sqlite_vec.__file__).parent)

# Hidden imports that PyInstaller may miss
hidden_imports = [
    # Core
    'core',
    'core.config',
    'core.database',
    'core.capture',
    'core.processor',
    'core.embeddings',
    'core.compression',

    # API
    'api',
    'api.main',
    'api.routes',
    'api.routes.status',
    'api.routes.recording',
    'api.routes.sync',
    'api.routes.search',
    'api.routes.screenshots',
    'api.routes.compression',
    'api.schemas',

    # Tray
    'tray',
    'tray.app',
    'tray.backend',
    'tray.api_client',
    'tray.config',
    'tray.icons',
    'tray.menu',

    # FastAPI/Uvicorn
    'uvicorn',
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'fastapi',
    'starlette',
    'pydantic',

    # ML/Embeddings (lazy loaded but need to be bundled)
    'sentence_transformers',
    'torch',
    'transformers',
    'huggingface_hub',

    # Image processing
    'PIL',
    'cv2',
    'skimage',
    'mss',

    # Database
    'sqlite_vec',

    # System tray
    'pystray',

    # Networking
    'httpx',

]

# Data files to include
datas = [
    # Web UI static files
    (WEB_OUT, 'web/out'),
    # sqlite_vec native library (must be in sqlite_vec/ for import to work)
    (SQLITE_VEC_DIR, 'sqlite_vec'),
]

# Binaries to exclude (to reduce size)
excludes = [
    'tkinter',
    'matplotlib',
    'pandas',
    'IPython',
    'jupyter',
    'notebook',
]

# Analysis
a = Analysis(
    [ENTRY_POINT],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# Remove unnecessary files to reduce size
# Filter out test files, docs, etc.
a.datas = [d for d in a.datas if not any(x in d[0] for x in [
    'tests/',
    '__pycache__',
    '.pyc',
    'test_',
    '_test.py',
])]

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

if IS_MACOS:
    # macOS: Create .app bundle
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name=APP_NAME,
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=False,  # No terminal window
        icon=ICON_MACOS,
    )

    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=False,
        upx_exclude=[],
        name=APP_NAME,
    )

    app = BUNDLE(
        coll,
        name=f'{APP_NAME}.app',
        icon=ICON_MACOS,
        bundle_identifier=APP_BUNDLE_ID,
        info_plist={
            'CFBundleName': APP_NAME,
            'CFBundleDisplayName': APP_NAME,
            'CFBundleVersion': APP_VERSION,
            'CFBundleShortVersionString': APP_VERSION,
            'CFBundleIdentifier': APP_BUNDLE_ID,
            'LSUIElement': True,  # Hide from Dock (menu bar app)
            'NSHighResolutionCapable': True,
            'LSMinimumSystemVersion': '10.15',
        },
    )

else:
    # Windows/Linux: Create single executable
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name=APP_NAME,
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=False,  # No terminal window
        icon=ICON_WINDOWS,
    )
