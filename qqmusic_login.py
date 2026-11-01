"""Interactive QQ Music login for the packaged Windows AstrBot plugin."""

import argparse
import asyncio
import importlib.util
import os
import sys
from pathlib import Path
from types import MappingProxyType


def apply_qqmusic_cookie_fix():
    """Handle empty response cookies in this process without editing dependencies."""
    from qqmusic_api.core import executor, response

    def safe_snapshot(raw):
        return response.RawPayload(
            status_code=raw.status_code,
            url=raw.url,
            headers=MappingProxyType(raw.headers),
            cookies={
                name: value if value is not None else ""
                for name, value in raw.cookies.items()
            },
            content=raw.content or b"",
            text=raw.text or "",
        )

    response.snapshot_payload = safe_snapshot
    executor.snapshot_payload = safe_snapshot


def load_auth():
    spec = importlib.util.spec_from_file_location(
        "packaged_qqmusic_auth", Path(__file__).resolve().with_name("qqmusic_auth.py")
    )
    auth = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(auth)
    return auth


async def login(show: bool):
    from qqmusic_api import Client
    from qqmusic_api.models.login import QRCodeLoginEvents, QRLoginType

    if sys.platform != "win32":
        raise RuntimeError("This login helper uses Windows DPAPI")
    apply_qqmusic_cookie_fix()
    auth = load_auth()
    qr_path = auth.CREDENTIAL_PATH.with_name("qqmusic-login-qr.png")
    async with Client(device_path=auth.get_device_path()) as client:
        qr = await client.login.get_qrcode(QRLoginType.QQ)
        qr_path.parent.mkdir(parents=True, exist_ok=True)
        qr_path.write_bytes(qr.data)
        print(f"QR_READY: {qr_path}", flush=True)
        print("Use mobile QQ to scan and confirm QQ Music login.", flush=True)
        if show:
            os.startfile(qr_path)
        previous = None
        try:
            async with asyncio.timeout(180):
                while True:
                    result = await client.login.check_qrcode(qr)
                    if result.event != previous:
                        print(result.event.name, flush=True)
                        previous = result.event
                    if result.event == QRCodeLoginEvents.DONE:
                        if (
                            result.credential is None
                            or not result.credential.is_valid()
                        ):
                            raise RuntimeError("Login returned no valid credential")
                        auth.save_credential(result.credential)
                        restored = auth.load_credential()
                        if restored is None or not restored.is_valid():
                            raise RuntimeError(
                                "Encrypted credential verification failed"
                            )
                        print("LOGIN_SAVED (Windows DPAPI encrypted)", flush=True)
                        return
                    if result.event in {
                        QRCodeLoginEvents.TIMEOUT,
                        QRCodeLoginEvents.REFUSE,
                    }:
                        return
                    await asyncio.sleep(3)
        finally:
            qr_path.unlink(missing_ok=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--show", action="store_true", help="Open the official QR image"
    )
    args = parser.parse_args()
    try:
        asyncio.run(login(args.show))
    except Exception as exc:
        print(f"LOGIN_FAILED: {type(exc).__name__}", file=sys.stderr)
        sys.exit(1)
