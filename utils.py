import errno
import winreg as registry

def _get_reg_value(regKey, valueKey):
    try:
        return registry.QueryValueEx(regKey, valueKey)[0]
    except OSError as e:
        return None

def get_uninstall_programs_list():
    uninstall_key = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
    programs = list()

    def list_programs(key, subKey=uninstall_key, debug_key=""):
        nonlocal programs

        regKey = registry.OpenKey(key, subKey)
        keys, values, last_modified = registry.QueryInfoKey(regKey)

        for i in range(keys):
            with registry.OpenKey(regKey, registry.EnumKey(regKey, i)) as itemKey:
                program = {
                    'DisplayIcon': _get_reg_value(itemKey, 'DisplayIcon'),
                    'DisplayVersion': _get_reg_value(itemKey, 'DisplayVersion'),
                    'DisplayName': _get_reg_value(itemKey, 'DisplayName'),
                    'InstallLocation': _get_reg_value(itemKey, 'InstallLocation'),
                    'Publisher': _get_reg_value(itemKey, 'Publisher'),
                    'UninstallString': _get_reg_value(itemKey, 'UninstallString'),
                    'URLInfoAbout': _get_reg_value(itemKey, 'URLInfoAbout'),
                    'Path': _get_reg_value(itemKey, 'Path'),
                    'RegistryKeyName': str(itemKey),
                    'DebugKey': debug_key
                }
                
                programs.append(program)
    
    list_programs(registry.HKEY_LOCAL_MACHINE, debug_key="LOCAL_MACHINE")
    list_programs(registry.HKEY_CURRENT_USER, debug_key="CURRENT_USER")

    return programs