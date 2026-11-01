"""Store QQ Music login credentials with Windows user-bound encryption."""

import ctypes
from ctypes import wintypes
from pathlib import Path

CREDENTIAL_PATH = (
    Path(__file__).resolve().parents[2]
    / "plugin_data"
    / "astrbot_plugin_matsuko_cover"
    / "qqmusic_credential.dpapi"
)
DEVICE_PATH = CREDENTIAL_PATH.with_name("qqmusic_device.json")


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def _crypt(data: bytes, *, decrypt: bool) -> bytes:
    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p
    buffer = ctypes.create_string_buffer(data)
    source = _DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte)))
    destination = _DataBlob()
    if decrypt:
        result = crypt32.CryptUnprotectData(
            ctypes.byref(source), None, None, None, None, 1, ctypes.byref(destination)
        )
    else:
        result = crypt32.CryptProtectData(
            ctypes.byref(source),
            "AstrBot QQ Music",
            None,
            None,
            None,
            1,
            ctypes.byref(destination),
        )
    if not result:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(destination.pbData, destination.cbData)
    finally:
        kernel32.LocalFree(destination.pbData)


def save_credential(credential) -> None:
    CREDENTIAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = credential.model_dump_json(by_alias=True).encode("utf-8")
    temporary = CREDENTIAL_PATH.with_suffix(".tmp")
    temporary.write_bytes(_crypt(payload, decrypt=False))
    temporary.replace(CREDENTIAL_PATH)


def load_credential():
    if not CREDENTIAL_PATH.is_file():
        return None
    from qqmusic_api.models.request import Credential

    return Credential.model_validate_json(
        _crypt(CREDENTIAL_PATH.read_bytes(), decrypt=True)
    )


def get_device_path() -> str:
    DEVICE_PATH.parent.mkdir(parents=True, exist_ok=True)
    return str(DEVICE_PATH)
