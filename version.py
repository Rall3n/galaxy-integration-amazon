__version__ = "0.2.0"

__changelog__ = {
    "0.2.0": '''
        - Replace "Twitch Prime" with "Prime Gaming"
        - Add timeout for library updates
            - Owned games: every 10 minutes
            - Installed games: every minute
        - Fetch installed games from SQLite database instead of registry
        - Minor improvements
    ''',
    "0.1.1": '''
        - Add OSCompatability check to allow installation of games
    ''',
    "0.1.0": '''
        - Initial Version
    '''
}
