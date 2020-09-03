import errno
import os
import sys
import subprocess
import re
import logging
import psutil

from pathlib import Path

from utils import get_uninstall_programs_list

class AmazonGamesClient:
    _CLIENT_NAME_ = 'Amazon Games'
    install_location = ""

    def __init__(self):
        self._get_install_location()

    def _get_install_location(self):
        programs = get_uninstall_programs_list()

        for program in programs:
            if program['DisplayName'] == self._CLIENT_NAME_:
                self.install_location = program['InstallLocation']
                break

    def update_install_location(self):
        if not self.install_location or not Path(self.install_location).resolve().exists():
            self._get_install_location()


    @staticmethod
    def _exec(args, cwd=None):
        subprocess.Popen(
            args,
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW,
            cwd=cwd,
            shell=True
        )

    @property
    def is_installed(self):
        if (not self.install_location or not os.path.exists(self.install_location)):
            return False
        else:
            return True
    
    @property
    def is_running(self):
        for proc in psutil.process_iter(attrs=['exe'], ad_value=''):
            if proc.info['exe'] == self.exec_path:
                return True

        return False

    @property
    def exec_path(self):
        if self.install_location:
            return os.path.join(self.install_location, "App", "Amazon Games.exe")
        else:
            return ""

    @property
    def owned_games_db_path(self):
        if self.install_location:
            return Path(self.install_location, '..', 'Data', 'Games', 'Sql', 'GameProductInfo.sqlite').resolve()

    @property
    def installed_games_db_path(self):
        if self.install_location:
            return Path(self.install_location, '..', 'Data', 'Games', 'Sql', 'GameInstallInfo.sqlite').resolve()

    @property
    def cookies_path(self):
        if self.install_location:
            return os.path.join(self.install_location, "Electron3", "Cookies")

    def get_installed_games(self):
        for program in get_uninstall_programs_list():
            if not program['UninstallString'] or 'Amazon Game Remover.exe'.lower() not in program['UninstallString'].lower():
                # self.logger.info(f"LocalGame - UninstallString: {program['DisplayName']} {program['UninstallString']}")
                continue
            
            if not os.path.exists(os.path.abspath(program['InstallLocation'])):
                # self.logger.info(f"LocalGame - InstallLocation: {program['DisplayName']} {program['InstallLocation']}")
                continue

            game_id = re.search(r'-p\s([a-z\d\-]+)', program['UninstallString'])[1]
            
            yield {
                'game_id': game_id,
                'program': program
            }

    # TODO: Get next "Amazon Games Remove.exe" with arguments "-m Game -p {game_id}"
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
            for proc in psutil.process_iter(attrs=['exe'], ad_value=''):
                if proc.info['exe'] == self.exec_path:
                    for child in proc.children():
                        child.terminate()
                    proc.terminate()
                    break