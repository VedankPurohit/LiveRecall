#!/usr/bin/env python3
"""
LiveRecall Release Builder
One-click script to build distributable packages from source.

Usage:
    python scripts/build_release.py             # Full build (always rebuilds web UI)
    python scripts/build_release.py --skip-web  # Skip web rebuild (use existing)

This script will:
1. Check prerequisites (Python, Node.js, uv)
2. Install Python dependencies
3. Install Node.js dependencies
4. Build Next.js static export
5. Generate app icons
6. Run PyInstaller to create app bundle
7. Create platform-specific installer (DMG on macOS, EXE on Windows)
"""

import argparse
import platform
import shutil
import subprocess
import sys
from pathlib import Path

# ============================================================================
# Configuration
# ============================================================================
VERSION = "0.1.2"
APP_NAME = "LiveRecall"
ROOT = Path(__file__).parent.parent.resolve()

# Required tools
REQUIRED_PYTHON_VERSION = (3, 10)
REQUIRED_NODE_VERSION = 18


# Colors for terminal output
class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    END = "\033[0m"
    BOLD = "\033[1m"


def print_step(msg: str):
    print(f"\n{Colors.BLUE}{Colors.BOLD}==>{Colors.END} {Colors.BOLD}{msg}{Colors.END}")


def print_success(msg: str):
    print(f"{Colors.GREEN}✓{Colors.END} {msg}")


def print_warning(msg: str):
    print(f"{Colors.YELLOW}⚠{Colors.END} {msg}")


def print_error(msg: str):
    print(f"{Colors.RED}✗{Colors.END} {msg}")


def run(cmd: list[str], cwd: Path = ROOT, check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    """Run a command"""
    print(f"  $ {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=cwd, check=check, capture_output=capture, text=True)


# ============================================================================
# Prerequisite Checks
# ============================================================================
def check_python() -> bool:
    """Check Python version"""
    version = sys.version_info[:2]
    if version >= REQUIRED_PYTHON_VERSION:
        print_success(
            f"Python {version[0]}.{version[1]} (>= {REQUIRED_PYTHON_VERSION[0]}.{REQUIRED_PYTHON_VERSION[1]})"
        )
        return True
    else:
        print_error(
            f"Python {version[0]}.{version[1]} (need >= {REQUIRED_PYTHON_VERSION[0]}.{REQUIRED_PYTHON_VERSION[1]})"
        )
        return False


def check_node() -> bool:
    """Check Node.js is installed"""
    try:
        result = run(["node", "--version"], capture=True, check=False)
        if result.returncode == 0:
            version = result.stdout.strip()
            # Extract major version number
            major = int(version.lstrip("v").split(".")[0])
            if major >= REQUIRED_NODE_VERSION:
                print_success(f"Node.js {version} (>= {REQUIRED_NODE_VERSION})")
                return True
            else:
                print_error(f"Node.js {version} (need >= {REQUIRED_NODE_VERSION})")
                return False
    except FileNotFoundError:
        pass
    print_error("Node.js not found. Install from https://nodejs.org/")
    return False


def check_uv() -> bool:
    """Check uv is installed"""
    try:
        result = run(["uv", "--version"], capture=True, check=False)
        if result.returncode == 0:
            print_success(f"uv {result.stdout.strip()}")
            return True
    except FileNotFoundError:
        pass
    print_warning("uv not found. Will use pip instead.")
    return False


def check_prerequisites() -> bool:
    """Check all prerequisites"""
    print_step("Checking prerequisites")

    python_ok = check_python()
    node_ok = check_node()
    check_uv()  # Check for uv, result used later via shutil.which

    return python_ok and node_ok


# ============================================================================
# Build Steps
# ============================================================================
def install_python_deps(use_uv: bool):
    """Install Python dependencies"""
    print_step("Installing Python dependencies")

    if use_uv:
        # uv sync installs all deps including dev-dependencies (pyinstaller)
        run(["uv", "sync"])
    else:
        run([sys.executable, "-m", "pip", "install", "-e", ".[dev,build]"])

    print_success("Python dependencies installed")


def install_node_deps():
    """Install Node.js dependencies"""
    print_step("Installing Node.js dependencies")

    web_dir = ROOT / "web"
    if not (web_dir / "node_modules").exists():
        run(["npm", "install"], cwd=web_dir)
        print_success("Node.js dependencies installed")
    else:
        print_success("Node.js dependencies already installed")


def build_web(skip: bool = False):
    """Build Next.js static export"""
    print_step("Building web UI")

    web_dir = ROOT / "web"
    out_dir = web_dir / "out"

    if skip and out_dir.exists() and (out_dir / "index.html").exists():
        print_warning("Skipping web rebuild (--skip-web). Using existing build.")
        return

    # Always clean and rebuild to ensure we have the latest code
    if out_dir.exists():
        print("  Cleaning previous web build...")
        shutil.rmtree(out_dir)

    run(["npm", "run", "build"], cwd=web_dir)

    if (out_dir / "index.html").exists():
        print_success("Web UI built successfully")
    else:
        raise RuntimeError("Web build failed - index.html not found")


def generate_icons(use_uv: bool):
    """Generate app icons"""
    print_step("Generating app icons")

    assets_dir = ROOT / "assets"

    # Check if icons already exist
    if (assets_dir / "icon.png").exists():
        print_success("Icons already generated")
        return

    # Run icon generator
    icon_script = ROOT / "scripts" / "generate_icons.py"
    if icon_script.exists():
        if use_uv:
            run(["uv", "run", "python", str(icon_script)])
        else:
            run([sys.executable, str(icon_script)])
        print_success("Icons generated")
    else:
        print_warning("Icon generator not found, skipping")


def build_pyinstaller(use_uv: bool):
    """Build with PyInstaller"""
    print_step("Building with PyInstaller")

    # Clean previous builds
    for d in ["build", "dist"]:
        path = ROOT / d
        if path.exists():
            print(f"  Cleaning {d}/")
            shutil.rmtree(path)

    # Run PyInstaller
    spec_file = ROOT / "liverecall.spec"
    if not spec_file.exists():
        raise RuntimeError("liverecall.spec not found")

    if use_uv:
        run(["uv", "run", "pyinstaller", str(spec_file), "--noconfirm"])
    else:
        run(["pyinstaller", str(spec_file), "--noconfirm"])

    # Verify output
    system = platform.system()
    if system == "Darwin":
        app_path = ROOT / "dist" / f"{APP_NAME}.app"
        if not app_path.exists():
            raise RuntimeError(f"Build failed: {app_path} not found")

        size = sum(f.stat().st_size for f in app_path.rglob("*") if f.is_file())
        print_success(f"Built {app_path.name} ({size / 1024 / 1024:.0f} MB)")
        return app_path
    else:
        exe_path = ROOT / "dist" / f"{APP_NAME}.exe"
        if not exe_path.exists():
            exe_path = ROOT / "dist" / APP_NAME
        if not exe_path.exists():
            raise RuntimeError("Build failed: executable not found")

        print_success(f"Built {exe_path.name} ({exe_path.stat().st_size / 1024 / 1024:.0f} MB)")
        return exe_path


def create_dmg(app_path: Path) -> Path:
    """
    Create a macOS DMG installer containing the specified .app bundle and an "Applications" symlink for drag-and-drop installation.
    
    Parameters:
        app_path (Path): Path to the built `.app` bundle to include in the DMG.
    
    Returns:
        dmg_path (Path): Path to the created DMG file in the `dist/` directory.
    """
    print_step("Creating DMG installer")

    arch = platform.machine()
    dmg_name = f"{APP_NAME}-{VERSION}-macOS-{arch}.dmg"
    dmg_path = ROOT / "dist" / dmg_name

    # Create a staging folder with app + Applications symlink
    staging_dir = ROOT / "dist" / "dmg_staging"
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    staging_dir.mkdir(parents=True)

    # Copy app to staging
    staged_app = staging_dir / app_path.name
    shutil.copytree(app_path, staged_app)

    # Create Applications symlink for drag-and-drop install
    applications_link = staging_dir / "Applications"
    applications_link.symlink_to("/Applications")

    if dmg_path.exists():
        dmg_path.unlink()

    run(
        [
            "hdiutil",
            "create",
            "-volname",
            APP_NAME,
            "-srcfolder",
            str(staging_dir),
            "-ov",
            "-format",
            "UDZO",
            str(dmg_path),
        ]
    )

    # Cleanup staging
    shutil.rmtree(staging_dir)

    print_success(f"Created {dmg_name} ({dmg_path.stat().st_size / 1024 / 1024:.0f} MB)")
    return dmg_path


def create_windows_zip(exe_path: Path) -> Path:
    """
    Create a Windows ZIP archive containing the built executable or PyInstaller output directory.
    
    The archive is written to dist/ and named "{APP_NAME}-{VERSION}-Windows-{arch}.zip", where common machine identifiers "AMD64" and "x86_64" are mapped to "x64". If exe_path is a file it is added as a single entry; if it is a directory its files are added preserving paths relative to exe_path.parent.
    
    Parameters:
        exe_path (Path): Path to the built executable file or the PyInstaller output directory to include in the ZIP.
    
    Returns:
        Path: Path to the created ZIP archive.
    """
    import zipfile

    print_step("Creating Windows ZIP archive")

    arch = platform.machine()
    # Map platform.machine() to common names
    arch_name = "x64" if arch in ("AMD64", "x86_64") else arch
    zip_name = f"{APP_NAME}-{VERSION}-Windows-{arch_name}.zip"
    zip_path = ROOT / "dist" / zip_name

    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        if exe_path.is_file():
            # Single-file EXE
            zf.write(exe_path, exe_path.name)
        elif exe_path.is_dir():
            # Directory with multiple files (if using COLLECT in PyInstaller)
            for file in exe_path.rglob("*"):
                if file.is_file():
                    arcname = file.relative_to(exe_path.parent)
                    zf.write(file, arcname)

    print_success(f"Created {zip_name} ({zip_path.stat().st_size / 1024 / 1024:.1f} MB)")
    return zip_path


def create_windows_installer(exe_path: Path) -> Path | None:
    """
    Create a Windows installer executable using NSIS.
    
    Uses the NSIS `makensis` tool to compile the installer script at installer/windows.nsi, passing the provided build artifact path into the script. If NSIS is not installed, the NSIS script is missing, or the build fails, the function skips creation and returns `None`.
    
    Parameters:
        exe_path (Path): Path to the built application executable (or the dist folder) to be embedded or referenced by the NSIS script.
    
    Returns:
        Path | None: Path to the created installer .exe on success, or `None` if installer creation was skipped or failed.
    """
    print_step("Creating Windows installer")

    nsis_available = shutil.which("makensis")

    if not nsis_available:
        print_warning("NSIS not found. Skipping installer creation.")
        print_warning("Install NSIS from: https://nsis.sourceforge.io/")
        return None

    nsi_script = ROOT / "installer" / "windows.nsi"
    if not nsi_script.exists():
        print_warning(f"NSIS script not found: {nsi_script}")
        print_warning("Skipping installer creation.")
        return None

    arch = platform.machine()
    arch_name = "x64" if arch in ("AMD64", "x86_64") else arch
    installer_name = f"{APP_NAME}-{VERSION}-Windows-{arch_name}-Setup.exe"
    installer_path = ROOT / "dist" / installer_name

    try:
        run(
            [
                "makensis",
                f"/DVERSION={VERSION}",
                f"/DEXE_PATH={exe_path}",
                f"/DOUTFILE={installer_path}",
                str(nsi_script),
            ]
        )
        print_success(f"Created {installer_name} ({installer_path.stat().st_size / 1024 / 1024:.1f} MB)")
        return installer_path
    except subprocess.CalledProcessError as e:
        print_error(f"NSIS build failed: {e}")
        return None


# ============================================================================
# Main
# ============================================================================
def main():
    """
    Orchestrates the full LiveRecall release build, producing platform-specific distributables.
    
    Parses CLI flags (--skip-web, --skip-dmg, --skip-installer, --skip-zip), verifies prerequisites, installs dependencies, builds the web UI (unless skipped), generates icons, runs PyInstaller to produce the application artifact, and then creates platform packages (DMG on macOS unless skipped; ZIP and optional NSIS installer on Windows). On failure the process exits with a non-zero status.
    """
    parser = argparse.ArgumentParser(
        description="Build LiveRecall distributable package",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/build_release.py             # Full build (always rebuilds web UI)
  python scripts/build_release.py --skip-web  # Skip web rebuild (use existing)
  python scripts/build_release.py --skip-installer  # Skip installer creation (Windows)
        """,
    )
    parser.add_argument("--skip-web", action="store_true", help="Skip web rebuild (use existing build)")
    parser.add_argument("--skip-dmg", action="store_true", help="Skip DMG creation (macOS)")
    parser.add_argument("--skip-installer", action="store_true", help="Skip installer creation (Windows)")
    parser.add_argument("--skip-zip", action="store_true", help="Skip ZIP creation (Windows)")
    args = parser.parse_args()

    print(f"\n{Colors.HEADER}{Colors.BOLD}LiveRecall Release Builder v{VERSION}{Colors.END}")
    print(f"Platform: {platform.system()} {platform.machine()}")
    print(f"Python: {sys.version.split()[0]}")
    print(f"Root: {ROOT}")

    # Check prerequisites
    if not check_prerequisites():
        print_error("\nPrerequisites not met. Please install missing tools.")
        sys.exit(1)

    use_uv = shutil.which("uv") is not None

    try:
        # Step 1: Install dependencies
        install_python_deps(use_uv)
        install_node_deps()

        # Step 2: Build web UI
        build_web(skip=args.skip_web)

        # Step 3: Generate icons
        generate_icons(use_uv)

        # Step 4: Build with PyInstaller
        artifact = build_pyinstaller(use_uv)

        # Step 5: Create platform package
        system = platform.system()
        if system == "Darwin":
            # macOS: Create DMG installer
            dmg = None
            if not args.skip_dmg:
                dmg = create_dmg(artifact)

            print(f"\n{Colors.GREEN}{Colors.BOLD}Build complete!{Colors.END}")
            print("\nOutput files:")
            print(f"  App:  {artifact}")
            if dmg:
                print(f"  DMG:  {dmg}")
                print("\nTo install: Open the DMG and drag LiveRecall to Applications")
            else:
                print("\nTo install: Right-click the .app and select Open")

        elif system == "Windows":
            # Windows: Create ZIP (always) and installer (optional)
            zip_file = None
            installer_file = None

            if not args.skip_zip:
                zip_file = create_windows_zip(artifact)

            if not args.skip_installer:
                installer_file = create_windows_installer(artifact)

            print(f"\n{Colors.GREEN}{Colors.BOLD}Build complete!{Colors.END}")
            print("\nOutput files:")
            print(f"  EXE:  {artifact}")
            if zip_file:
                print(f"  ZIP:  {zip_file}")
            if installer_file:
                print(f"  Installer:  {installer_file}")
            print("\nTo install: Extract ZIP or run the installer")

        else:
            # Linux (future)
            print(f"\n{Colors.GREEN}{Colors.BOLD}Build complete!{Colors.END}")
            print(f"\nOutput: {artifact}")

    except subprocess.CalledProcessError as e:
        print_error(f"\nBuild failed: {e}")
        sys.exit(1)
    except Exception as e:
        print_error(f"\nBuild failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()