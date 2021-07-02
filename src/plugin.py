import asyncio
import json
import logging
import os
import subprocess
import sys
import webbrowser

from galaxy.api.plugin import Plugin, create_and_run_plugin
from galaxy.api.consts import Feature, Platform, LicenseType, LocalGameState, OSCompatibility
from galaxy.api.types import Authentication, Game, GameTime, LicenseInfo, LocalGame
from time import time
from typing import List

from version import __version__
from client import AmazonGamesClient
from db_client import DBClient
from authentication import create_next_step, START_URI, END_URI


LOCAL_GAMES_TIMEOUT = (1 * 60)
OWNED_GAMES_TIMEOUT = (10 * 60)
FALLBACK_SYNC_TIMEOUT = (2.5 * 60)


class AmazonGamesPlugin(Plugin):
    _owned_games_db = None
    _local_games_db = None
    _owned_games_last_updated = 0
    _local_games_last_updated = 0

    def __init__(self, reader, writer, token):
        super().__init__(Platform.Amazon, __version__, reader, writer, token)
        self.logger = logging.getLogger('amazonPlugin')
        self._client = AmazonGamesClient()
        
        self._local_games_cache = None
        self._owned_games_cache = None
        self.proc = None
        self.running_game_id = ""
        self.tick_count = 0

    def _init_db(self):
        if not self._owned_games_db:
            self._owned_games_db = DBClient(self._client.owned_games_db_path)

        if not self._local_games_db:
            self._local_games_db = DBClient(self._client.installed_games_db_path)

    def _on_auth(self):
        self.logger.info("Auth finished")
        self._init_db()

        self.store_credentials({ 'creds': 'dummy_data_because_local_app' })
        return Authentication('amazon_user_id', 'Amazon Games User')

    def _get_owned_games(self):
        try:
            return {
                row['ProductIdStr']: Game(row['ProductIdStr'], row['ProductTitle'], dlcs=None, license_info=LicenseInfo(LicenseType.SinglePurchase))
                for row in self._owned_games_db.select('DbSet', rows=['ProductIdStr', 'ProductTitle'])
            }
        except Exception:
            self.logger.exception('Failed to get owned games')
            return {}

    def _update_owned_games(self):
        if (time() - self._owned_games_last_updated) < OWNED_GAMES_TIMEOUT:
            return

        owned_games = self._get_owned_games()

        for game_id in self._owned_games_cache.keys() - owned_games.keys():
            self.remove_game(game_id)

        for game_id in (owned_games.keys() - self._owned_games_cache.keys()):
            self.add_game(owned_games[game_id])
        
        self._owned_games_cache = owned_games
        self._owned_games_last_updated = time()

    def _get_local_games(self):
        try:
            return {
                row['Id']: LocalGame(row['Id'], LocalGameState.Installed)
                for row in self._local_games_db.select('DbSet', rows=['Id', 'Installed']) if row['Installed']
            }
        except Exception:
            self.logger.exception('Failed to get local games')
            return {}

    def _update_local_games(self):
        if (time() - self._local_games_last_updated) < LOCAL_GAMES_TIMEOUT:
            return

        local_games = self._get_local_games()

        for game_id in self._local_games_cache.keys() - local_games.keys():
            self.update_local_game_status(LocalGame(game_id, LocalGameState.None_))

        for game_id, local_game in local_games.items():
            if self._client.game_running(game_id):
                local_game.local_game_state |= LocalGameState.Running

            old_game = self._local_games_cache.get(game_id)
            if old_game is None or old_game.local_game_state != local_game.local_game_state:
                self.update_local_game_status(local_game)

        self._local_games_cache = local_games
        self._local_games_last_updated = time()

    async def prepare_game_times_context(self, game_ids):
        return self._get_games_times_dict()

    async def get_game_time(self, game_id, context):
        game_time = context.get(game_id)
        return game_time


    def _get_games_times_dict(self) -> dict:
        ''' Returns a dict of GameTime objects
        
        Creates and reads the game_times.json file
        '''
        game_times = {}
        path = os.path.expandvars(r"%LOCALAPPDATA%\GOG.com\Galaxy\Configuration\plugins\amazon\game_times.json")
        update_file = False

        # Read the games times json
        try:
            with open(path, encoding="utf-8") as game_times_file:
                data = json.load(game_times_file)
        except FileNotFoundError:
            data = {}

            if not os.path.isdir(os.path.dirname(path)):
                os.makedirs(os.path.dirname(path))
                
            with open(path, "w", encoding="utf-8") as game_times_file:
                json.dump(data, game_times_file, indent=4)

        for game_id in self._local_games_cache.keys():
            if game_id in data:
                time_played = data.get(game_id).get("time_played")
                last_time_played = data.get(game_id).get("last_time_played")
            else:
                time_played = 0
                last_time_played = None
                data[game_id] = { "time_played": 0, "last_time_played": None }
                update_file = True
            
            game_times[game_id] = GameTime(game_id, time_played, last_time_played)

        if update_file == True:
            with open(path, "w", encoding="utf-8") as game_times_file:
                json.dump(data, game_times_file, indent=4)
        
        return game_times

    @staticmethod
    def _scheme_command(command, game_id):
        self.proc = subprocess.Popen(webbrowser.open(f'amazon-games://{command}/{game_id}'))

    async def _ensure_initialization(self):
        await asyncio.sleep(FALLBACK_SYNC_TIMEOUT)

        if not self._client.is_installed:
            return

        if not self._local_games_cache:
            self.logger.info('Fallback initialization of `_local_games_cache`')
            self._local_games_cache = {}

        if not self._owned_games_cache:
            self.logger.info('Fallback initialization of `_owned_games_cache`')
            self._owned_games_cache = {}

    #
    # Galaxy Plugin methods
    #

    async def authenticate(self, stored_credentials=None):
        self.logger.info("Plugin authenticate")

        if not stored_credentials:
            return create_next_step(START_URI.SPLASH, END_URI.SPLASH_CONTINUE)

        return self._on_auth()

    async def pass_login_credentials(self, step, credentials, cookies):
        if any(x in credentials['end_uri'] for x in ['splash_continue', 'missing_app_retry']):
            if not self._client.is_installed:
                return create_next_step(START_URI.MISSING_APP, END_URI.MISSING_APP_RETRY)

            return self._on_auth()

        return create_next_step(START_URI.SPLASH, END_URI.SPLASH_CONTINUE)

    async def get_owned_games(self):
        if self._owned_games_cache is None:
            self._owned_games_last_updated = time()
            self._owned_games_cache = self._get_owned_games()
        return list(self._owned_games_cache.values())

    async def get_local_games(self):
        if self._local_games_cache is None:
            self._local_games_last_updated = time()
            self._local_games_cache = self._get_local_games()
        return list(self._local_games_cache.values())

    def handshake_complete(self) -> None:
        self.create_task(self._ensure_initialization(), '_ensure_initialization')

    def tick(self):
        self.tick_count += 1
        self._check_game_status
        self._client.update_install_location()
        if self._client.is_installed:
            if self._owned_games_db and self._owned_games_cache is not None:
                self._update_owned_games()

            if self._local_games_db and self._local_games_cache is not None:
                self._update_local_games()

            if self.tick_count % 12 == 0:
                self._update_all_game_times()

    def _check_game_status(self) -> None:
        try:
            if self.proc.poll() is not None:
                self._client._set_session_end()
                session_duration = self._client._get_session_duration()
                last_time_played = int(time.time())
                self._update_game_time(self.running_game_id, session_duration, last_time_played)
                self.proc = None
                self.running_game_id = ""
        except AttributeError:
            pass
    
    async def _update_all_game_times(self) -> None:
        loop = asyncio.get_running_loop()
        new_game_times = await loop.run_in_executor(None, self._get_games_times_dict)
        for game_time in new_game_times:
            self.update_game_time(new_game_times[game_time])


    def _update_game_time(self, game_id, session_duration, last_time_played) -> None:
        ''' Returns None 
        
        Update the game time of a single game
        '''
        path = os.path.expandvars(r"%LOCALAPPDATA%\GOG.com\Galaxy\Configuration\plugins\amazon\game_times.json")

        with open(path, encoding="utf-8") as game_times_file:
            data = json.load(game_times_file)

        data[game_id]["time_played"] = data.get(game_id).get("time_played") + session_duration
        data[game_id]["last_time_played"] = last_time_played

        with open(path, "w", encoding="utf-8") as game_times_file:
            json.dump(data, game_times_file, indent=4)

        self.update_game_time(GameTime(game_id, data.get(game_id).get("time_played"), last_time_played))

    async def launch_game(self, game_id):
        AmazonGamesPlugin._scheme_command('play', game_id)
        self.running_game_id = game_id
        self._client._set_session_start()

    async def uninstall_game(self, game_id):
        self.logger.info(f'Uninstalling game {game_id}')
        self._client.uninstall_game(game_id)

    async def launch_platform_client(self):
        self._client.start_client()

    async def shutdown_platform_client(self):
        self._client.stop_client()

    async def get_os_compatibility(self, game_id, context):
        return OSCompatibility.Windows

    @property
    def features(self) -> List[Feature]:
        # As we can't remove the `install_game` method, we just skip the `Feature` from the features list
        return [x for x in list(self._features) if x not in [Feature.InstallGame]]

def main():
    create_and_run_plugin(AmazonGamesPlugin, sys.argv)


# run plugin event loop
if __name__ == "__main__":
    main()
