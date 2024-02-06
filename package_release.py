"""Entire release creation - including source code and EXE."""
import os
import pathlib
import shutil
import subprocess


FOLDER = pathlib.Path(__file__).parent
RELEASE_FOLDER = FOLDER / "release"
if RELEASE_FOLDER.is_dir():
    shutil.rmtree(RELEASE_FOLDER)
RELEASE_FOLDER.mkdir()

CODE_PACKAGE_FOLDER = RELEASE_FOLDER / "code"
CODE_PACKAGE_ZIP = RELEASE_FOLDER / "code"

ICON = FOLDER / "src" / "gui" / "bin" / "icon.ico"
START_SCRIPT = FOLDER / "run_app.py"

PATHS = (
    FOLDER / "src",
    FOLDER / "src" / "gui"
)
BINARIES = {
    FOLDER / "src" / "gui" / "cpp" / "conversion.so": "src/gui/cpp",
    FOLDER / "src" / "gui" / "cpp" / "foreground.so": "src/gui/cpp",
}
ADDITIONAL_DATA = {
    FOLDER / "src" / "gui" / "bin": "src/gui/bin/"
}
OUTPUT_EXE_NAME = RELEASE_FOLDER / "streetviewimagedownloader.exe"


def package_code() -> None:
    """Packages source, ready to run."""
    CODE_PACKAGE_FOLDER.mkdir()
    shutil.copy(START_SCRIPT, CODE_PACKAGE_FOLDER / START_SCRIPT.name)
    # Copy source folder.
    shutil.copytree(FOLDER / "src", CODE_PACKAGE_FOLDER / "src")
    # Delete all pycaches.
    for path in (CODE_PACKAGE_FOLDER / "src").rglob("__pycache__"):
        shutil.rmtree(path)
    # Make zip file.
    shutil.make_archive(CODE_PACKAGE_ZIP, "zip", CODE_PACKAGE_FOLDER)
    # Delete copied source folder.
    shutil.rmtree(CODE_PACKAGE_FOLDER)


def package_exe() -> None:
    """Packages standalone EXE, ready to run."""
    # Build command parts.
    command_parts = [
        "pyinstaller", str(START_SCRIPT), "--noconfirm", "--onefile",
        "--windowed",  "--icon", str(ICON)]
    for binary_src, binary_dest in BINARIES.items():
        command_parts.append("--add-binary")
        command_parts.append(f"{binary_src};{binary_dest}")
    for path in PATHS:
        command_parts.append("--paths")
        command_parts.append(str(path))
    for add_data_src, add_data_dest in ADDITIONAL_DATA.items():
        command_parts.append("--add-data")
        command_parts.append(f"{add_data_src};{add_data_dest}")
    # Run Pyinstaller.
    os.chdir(RELEASE_FOLDER)
    subprocess.run(command_parts)
    # Renames output EXE.
    output_exe = RELEASE_FOLDER / "dist" / f"{START_SCRIPT.stem}.exe"
    output_exe.rename(OUTPUT_EXE_NAME)
    # Deletes Pyinstaller files and folders.
    (RELEASE_FOLDER / "dist").rmdir()
    shutil.rmtree(RELEASE_FOLDER / "build")
    (RELEASE_FOLDER / f"{START_SCRIPT.stem}.spec").unlink(True)


def main() -> None:
    package_code()
    package_exe()


if __name__ == "__main__":
    main()
