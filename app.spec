# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Statik dosyaları ve şablonları dahil etme
added_files = [
    ('templates', 'templates'),
    ('static', 'static'),
    ('uploads', 'uploads'),
    ('rules.json', '.'),
    ('missing_rules.json', '.'),
    ('ana_tablo.csv', '.'),
    ('Kategoriler.csv', '.')
]

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=['pandas', 'plotly', 'matplotlib.backends.backend_agg', 'flask', 'werkzeug', 'markupsafe', 'jinja2'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Analiz Uygulaması',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='static/favicon.ico'
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Analiz Uygulaması',
)
