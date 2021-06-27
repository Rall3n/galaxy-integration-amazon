import os
import re
import subprocess

from galaxy.proc_tools import process_iter
from pathlib import Path

from utils import get_uninstall_programs_list


class AmazonGamesClient:
    _CLIENT_NAME_ = 'Amazon Games'
    install_location: Path = None

    def __init__(self):
        self._get_install_location()

    def _get_install_location(self):
        for program in get_uninstall_programs_list():
            if program['DisplayName'] == self._CLIENT_NAME_:
                self.install_location = Path(program['InstallLocation']).resolve()
                break

    def update_install_location(self):
        if not self.install_location or not self.install_location.exists():
            self._get_install_location()


    @staticmethod
    def _exec(args, cwd=None):
        subprocess.Popen(
            args,
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW,
            cwd=cwd,
            shell=False
        )

    @property
    def is_installed(self):
        return self.install_location and self.install_location.exists()
    
    @property
    def is_running(self):
        for proc in process_iter():
            if proc.binary_path and Path(proc.binary_path).resolve() == self.exec_path:
                return True

        return False

    @property
    def exec_path(self):
        if not self.install_location:
            return ''

        return self.install_location.joinpath("Amazon Games.exe")

    @property
    def owned_games_db_path(self):
        if self.install_location:
            return self.install_location.joinpath('..', 'Data', 'Games', 'Sql', 'GameProductInfo.sqlite').resolve()

    @property
    def installed_games_db_path(self):
        if self.install_location:
            return self.install_location.joinpath('..', 'Data', 'Games', 'Sql', 'GameInstallInfo.sqlite').resolve()

    @property
    def cookies_path(self):
        if self.install_location:
            return self.install_location.joinpath("Electron3", "Cookies")

    def get_installed_games(self):
        for program in get_uninstall_programs_list():
            if not program['UninstallString'] or 'Amazon Game Remover.exe'.lower() not in program['UninstallString'].lower():
                continue
            
            if not os.path.exists(os.path.abspath(program['InstallLocation'])):
                continue

            game_id = re.search(r'-p\s([a-z\d\-]+)', program['UninstallString'])[1]
            
            yield {
                'game_id': game_id,
                'program': program
            }

    def uninstall_game(self, game_id):
        for game in self.get_installed_games():
            if game['game_id'] == game_id:
                AmazonGamesClient._exec(game["program"]["UninstallString"])
                break

    def start_client(self):
        if not self.is_running:
            AmazonGamesClient._exec(self.exec_path)

    def stop_client(self):
        if self.is_running:
            AmazonGamesClient._exec(f'taskkill /t /f /im "Amazon Games.exe"')

    def game_running(self, game_id):
        for game in self.get_installed_games():
            if game['game_id'] == game_id:
                for proc in process_iter():
                    if proc.binary_path and game['program']['InstallLocation'] in proc.binary_path:
                        return True
