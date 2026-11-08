# PyInstaller spec. Run from api/ after `npm run build:desktop` (in web/) and
# `python desktop/fetch_models.py`:  pyinstaller desktop/heal_tool.spec
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules, copy_metadata

api_dir = Path(SPECPATH).parent
web_dist = api_dir.parent / "web" / "dist"
models = api_dir / "models"

for required in (web_dist / "index.html", models):
    if not required.exists():
        raise SystemExit(f"Missing {required}; build the web app and fetch models first.")

a = Analysis(
    [str(api_dir / "desktop" / "app.py")],
    pathex=[str(api_dir / "src")],
    # artifacts.py reads these versions via importlib.metadata at startup.
    datas=[(str(web_dist), "web"), (str(models), "models")]
    + [
        item
        for package in ("numpy", "scipy", "scikit-learn", "joblib")
        for item in copy_metadata(package)
    ],
    hiddenimports=(
        collect_submodules("service")
        + collect_submodules("uvicorn")
        + collect_submodules("sklearn")
        + collect_submodules("scipy.special")
        + ["config", "landscape", "kriging", "artifacts"]
    ),
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="HEALTool",
    console=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name="HEALTool")

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="HEALTool.app",
        bundle_identifier="com.healstrata.healtool",
    )
