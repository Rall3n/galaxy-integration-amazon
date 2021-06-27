import winreg as registry

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
