import base64
import ctypes
import json
import sys
from ctypes import wintypes
from pathlib import Path


SETTINGS_FILE_NAME = "settings.json"


class DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_byte)),
    ]


crypt32 = ctypes.WinDLL(
    "crypt32",
    use_last_error=True,
)

kernel32 = ctypes.WinDLL(
    "kernel32",
    use_last_error=True,
)


crypt32.CryptProtectData.argtypes = [
    ctypes.POINTER(DATA_BLOB),
    wintypes.LPCWSTR,
    ctypes.POINTER(DATA_BLOB),
    ctypes.c_void_p,
    ctypes.c_void_p,
    wintypes.DWORD,
    ctypes.POINTER(DATA_BLOB),
]
crypt32.CryptProtectData.restype = wintypes.BOOL


crypt32.CryptUnprotectData.argtypes = [
    ctypes.POINTER(DATA_BLOB),
    ctypes.POINTER(wintypes.LPWSTR),
    ctypes.POINTER(DATA_BLOB),
    ctypes.c_void_p,
    ctypes.c_void_p,
    wintypes.DWORD,
    ctypes.POINTER(DATA_BLOB),
]
crypt32.CryptUnprotectData.restype = wintypes.BOOL


kernel32.LocalFree.argtypes = [
    ctypes.c_void_p,
]
kernel32.LocalFree.restype = ctypes.c_void_p


def get_app_directory():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent

    return Path(__file__).resolve().parent


def get_settings_path():
    return (
        get_app_directory()
        / SETTINGS_FILE_NAME
    )


def bytes_to_blob(data):
    buffer = ctypes.create_string_buffer(
        data,
        len(data),
    )

    blob = DATA_BLOB(
        len(data),
        ctypes.cast(
            buffer,
            ctypes.POINTER(ctypes.c_byte),
        ),
    )

    return blob, buffer


def encrypt_password(password):
    if not password:
        return ""

    data = password.encode("utf-8")
    input_blob, input_buffer = bytes_to_blob(data)
    output_blob = DATA_BLOB()

    success = crypt32.CryptProtectData(
        ctypes.byref(input_blob),
        None,
        None,
        None,
        None,
        0,
        ctypes.byref(output_blob),
    )

    if not success:
        raise ctypes.WinError(
            ctypes.get_last_error()
        )

    try:
        encrypted = ctypes.string_at(
            output_blob.pbData,
            output_blob.cbData,
        )

        return base64.b64encode(
            encrypted
        ).decode("ascii")

    finally:
        kernel32.LocalFree(
            output_blob.pbData
        )


def decrypt_password(encrypted_password):
    if not encrypted_password:
        return ""

    encrypted = base64.b64decode(
        encrypted_password
    )

    input_blob, input_buffer = bytes_to_blob(
        encrypted
    )
    output_blob = DATA_BLOB()

    success = crypt32.CryptUnprotectData(
        ctypes.byref(input_blob),
        None,
        None,
        None,
        None,
        0,
        ctypes.byref(output_blob),
    )

    if not success:
        raise ctypes.WinError(
            ctypes.get_last_error()
        )

    try:
        decrypted = ctypes.string_at(
            output_blob.pbData,
            output_blob.cbData,
        )

        return decrypted.decode("utf-8")

    finally:
        kernel32.LocalFree(
            output_blob.pbData
        )


def save_settings(
    font_size,
    password,
):
    settings = {
        "font_size": int(font_size),
        "obs_password": encrypt_password(
            password
        ),
    }

    settings_path = get_settings_path()

    with settings_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            settings,
            file,
            indent=2,
        )


def load_settings():
    settings_path = get_settings_path()

    if not settings_path.exists():
        return {}

    try:
        with settings_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            settings = json.load(file)

    except (
        OSError,
        json.JSONDecodeError,
    ):
        return {}

    result = {}

    font_size = settings.get(
        "font_size"
    )

    if isinstance(font_size, int):
        result["font_size"] = font_size

    encrypted_password = settings.get(
        "obs_password"
    )

    if isinstance(
        encrypted_password,
        str,
    ):
        try:
            result["password"] = (
                decrypt_password(
                    encrypted_password
                )
            )

        except Exception:
            # 설정 파일을 다른 PC/계정에서
            # 가져온 경우에도 앱 자체는 실행
            pass

    return result
