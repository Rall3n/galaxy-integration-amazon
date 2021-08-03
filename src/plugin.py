import asyncio
import logging
import sys
import webbrowser

from galaxy.api.plugin import Plugin, create_and_run_plugin
from galaxy.api.consts import Feature, Platform, LicenseType, LocalGameState, OSCompatibility
from galaxy.api.types import Authentication, Game, LicenseInfo, LocalGame
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
    _auth = False

    def __init__(self, reader, writer, token):
        super().__init__(Platform.Amazon, __version__, reader, writer, token)
        self.logger = logging.getLogger('amazonPlugin')
        self._client = AmazonGamesClient()

        self._local_games_cache = None
        self._owned_games_cache = None

    def _init_db(self):
        if not self._owned_games_db:
            self._owned_games_db = DBClient(self._client.owned_games_db_path)

        if not self._local_games_db:
            self._local_games_db = DBClient(self._client.installed_games_db_path)

    def _on_auth(self):
        self.logger.info("Auth finished")
        self._init_db()
        self._auth = True

        self.store_credentials({ 'creds': 'dummy_data_because_local_app' })
        return Authentication('amazon_user_id', 'Amazon Games User')

    async def _auth_finished(self):
        start = time()

        while (time() - 15 <= start):
            if (self._auth):
                return True
            
            await asyncio.sleep(0.5)

        return False

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

    @staticmethod
    def _scheme_command(command, game_id):
        webbrowser.open(f'amazon-games://{command}/{game_id}')

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
        # Since 2.0.38 Beta of the client `get_local_games` is called before auth is finished.
        # Problematic, as databases are set on auth.
        # So we wait until we have been authenticated.
        if not await self._auth_finished():
            return []

        if self._local_games_cache is None:
            self._local_games_last_updated = time()
            self._local_games_cache = self._get_local_games()
        return list(self._local_games_cache.values())

    def handshake_complete(self) -> None:
        self.create_task(self._ensure_initialization(), '_ensure_initialization')

    def tick(self):
        self._client.update_install_location()
        if self._client.is_installed:
            if self._owned_games_db and self._owned_games_cache is not None:
                self._update_owned_games()

            if self._local_games_db and self._local_games_cache is not None:
                self._update_local_games()

    async def launch_game(self, game_id):
        AmazonGamesPlugin._scheme_command('play', game_id)

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
