#!/usr/bin/env python3
"""Build the AWS Lambda deployment zip WITHOUT Docker.

    python scripts/build_lambda_zip.py        ->  build/airwatch-lambda.zip

How it works: pip downloads Linux (manylinux x86_64, CPython 3.12) wheels no matter which OS you are on,
the bundle is trimmed to fit Lambda's 250 MB unzipped limit, and our src/*.py is added at the zip root.
boto3 is NOT bundled: the Lambda Python runtime already provides it.

Lambda settings that match this zip: runtime Python 3.12, architecture x86_64, handler lambda_handler.handler
"""
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build"
PKG = BUILD / "package"
OUT = BUILD / "airwatch-lambda.zip"
LIMIT = 250 * 1024 * 1024  # Lambda: 250 MB unzipped (function + layers)
TRIM_TESTS_IN = ("pandas", "scipy", "sklearn")  # NOT numpy: numpy.testing imports numpy._core.tests at runtime


def size_of(path: Path) -> int:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def main() -> int:
    if BUILD.exists():
        shutil.rmtree(BUILD)
    PKG.mkdir(parents=True)

    print("1/4 downloading Linux wheels (about 1 minute)...")
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", "--quiet", "--no-cache-dir", "--target", str(PKG),
        "--platform", "manylinux2014_x86_64", "--implementation", "cp", "--python-version", "3.12",
        "--only-binary=:all:", "--upgrade", "-r", str(ROOT / "requirements-lambda.txt")])

    print("2/4 trimming...")
    for name in TRIM_TESTS_IN:
        for d in list((PKG / name).rglob("tests")) + list((PKG / name).rglob("test")):
            if d.is_dir():
                shutil.rmtree(d, ignore_errors=True)
    for d in list(PKG.rglob("__pycache__")):
        shutil.rmtree(d, ignore_errors=True)
    numpy_dir = PKG / "numpy"
    for f in list(PKG.rglob("*")):
        if f.is_file() and f.suffix in {".pyc", ".pyi", ".c", ".h", ".pxd", ".pyx"} and numpy_dir not in f.parents:
            f.unlink()
    for sub in ("data", "images", "descr"):
        shutil.rmtree(PKG / "sklearn" / "datasets" / sub, ignore_errors=True)

    print("3/4 adding project code...")
    for f in (ROOT / "src").glob("*.py"):
        shutil.copy2(f, PKG / f.name)

    total = size_of(PKG)
    print(f"    unzipped size: {total / 1024 / 1024:.0f} MB (Lambda limit 250 MB)")
    if total > LIMIT:
        print("ERROR: package is over Lambda's 250 MB limit. Do not deploy this zip.")
        return 1

    print("4/4 zipping...")
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for f in sorted(PKG.rglob("*")):
            if f.is_file():
                zi = zipfile.ZipInfo.from_file(f, f.relative_to(PKG).as_posix())
                zi.compress_type = zipfile.ZIP_DEFLATED
                zi.external_attr = 0o644 << 16  # world-readable: Lambda refuses unreadable files
                z.writestr(zi, f.read_bytes())
    print(f"done: {OUT}  ({OUT.stat().st_size / 1024 / 1024:.0f} MB zipped)")
    print("Too big for the Lambda console's direct upload (50 MB): upload it to S3 first, then use "
          "'Upload from > Amazon S3 location'. See README.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
