from ctypes import wintypes, byref, c_buffer, Structure, c_char, POINTER, cdll, windll
from typing import Union
import winreg as registry

CryptUnprotectData = windll.crypt32.CryptUnprotectData
CRYPTPROTECT_UI_FORBIDDEN = 0x01


def _get_reg_value(regKey, valueKey):
    try:
        return registry.QueryValueEx(regKey, valueKey)[0]
    except OSError:
        return None

def get_uninstall_programs_list():
    uninstall_key = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"

    def list_programs(key, subKey=uninstall_key, debug_key=""):
        regKey = registry.OpenKey(key, subKey)
        keys, _, _ = registry.QueryInfoKey(regKey)

        for i in range(keys):
            with registry.OpenKey(regKey, registry.EnumKey(regKey, i)) as itemKey:
                yield {
                    'DisplayName': _get_reg_value(itemKey, 'DisplayName'),
                    'InstallLocation': _get_reg_value(itemKey, 'InstallLocation'),
                    'UninstallString': _get_reg_value(itemKey, 'UninstallString')
                }

    yield from list_programs(registry.HKEY_CURRENT_USER, debug_key="CURRENT_USER")
    yield from list_programs(registry.HKEY_LOCAL_MACHINE, debug_key="LOCAL_MACHINE")


class DataBlob(Structure):
    _fields_ = [('cbData', wintypes.DWORD), ('pbData', POINTER(c_char))]


def crypt_unprotect_data(data: bytes) -> Union[bytes, None]:
    bufferIn = c_buffer(data, len(data))
    blobIn = DataBlob(len(data), bufferIn)
    blobOut = DataBlob()

    if CryptUnprotectData(byref(blobIn), None, None, None, None, CRYPTPROTECT_UI_FORBIDDEN, byref(blobOut)):
        cbData = int(blobOut.cbData)
        bufferOut = c_buffer(cbData)
        cdll.msvcrt.memcpy(bufferOut, blobOut.pbData, cbData)
        windll.kernel32.LocalFree(blobOut.pbData)
        return bufferOut.raw
    else:
        return None
