"""Build an AstrBot plugin ZIP from an explicit source-only allowlist."""

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = (
    "main.py",
    "api.py",
    "original_songs.py",
    "selection.py",
    "qq_callbacks.py",
    "qqmusic_auth.py",
    "qqmusic_login.py",
    "_conf_schema.json",
    "metadata.yaml",
    "requirements.txt",
    "config.example.json",
    "README.md",
    "README_UPSTREAM.md",
    "使用说明.md",
    "NOTICE.md",
    "CHANGELOG.md",
    "LICENSE",
    "logo.png",
)


def build(output: Path) -> Path:
    metadata = (ROOT / "metadata.yaml").read_text(encoding="utf-8")
    plugin_name = re.search(
        r"^name:\s*([A-Za-z_][A-Za-z_0-9]*)\s*$", metadata, re.MULTILINE
    ).group(1)
    version = re.search(
        r"^version:\s*v?([0-9A-Za-z.+-]+)\s*$", metadata, re.MULTILINE
    ).group(1)
    payload = {name: (ROOT / name).read_bytes() for name in FILES}
    for name, data in payload.items():
        if name.endswith(".py"):
            compile(data, name, "exec")
    manifest = {
        "plugin": plugin_name,
        "version": version,
        "files": {
            name: hashlib.sha256(data).hexdigest() for name, data in payload.items()
        },
    }
    payload["MANIFEST.json"] = (
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    ).encode("utf-8")
    output.mkdir(parents=True, exist_ok=True)
    destination = output / f"{manifest['plugin']}_v{version}.zip"
    with zipfile.ZipFile(
        destination, "w", zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for path, data in sorted(payload.items()):
            info = zipfile.ZipInfo(
                f"{manifest['plugin']}/{path}", date_time=(2026, 11, 2, 0, 0, 0)
            )
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    with zipfile.ZipFile(destination) as archive:
        assert archive.testzip() is None
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    destination.with_suffix(".zip.sha256").write_text(
        f"{digest}  {destination.name}\n", encoding="utf-8", newline="\n"
    )
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    print(build(args.output.resolve()))
