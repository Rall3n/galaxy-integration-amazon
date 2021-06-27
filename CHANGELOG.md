# Changelog

## 0.4.0
- Added `Running` state to local games
- Fixed app not closing after game closes
- Removed `InstallGame` feature due to no known way available to start the installation from outside the app
- Small improvements regarding registry access

## 0.3.1
- Security: Update `aiohttp` dependency

## 0.3.0
- Add workaround for missing/delayed library synchronisation
- Update splash wording in regards to end of game support in the Twitch App
- Update dependencies
- Fix switch of variables in library updates
- Fix error in logs if database table does not exist

## 0.2.0
- Replace "Twitch Prime" with "Prime Gaming"
- Add timeout for library updates
    - Owned games: every 10 minutes
    - Installed games: every minute
- Fetch installed games from SQLite database instead of registry
- Minor improvements

## 0.1.1
- Add OSCompatability check to allow installation of games

## 0.1.0
- Initial Version

