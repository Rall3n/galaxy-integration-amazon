from galaxy.api.types import NextStep
from pathlib import Path


_DIRNAME = Path(__file__).resolve().parent


_AUTH_PARAMS = {
    "window_title": "GOG Galaxy 2.0 - Amazon Games Integration",
    "window_width": 560,
    "window_height": 710,
    "start_uri": '',
    "end_uri_regex": ''
}


class START_URI():
    SPLASH = Path(_DIRNAME, 'splash', 'index.html').resolve().as_uri() + '?view=splash'
    MISSING_APP = Path(_DIRNAME, 'splash', 'index.html').resolve().as_uri() + '?view=missing-app'


class END_URI():
    SPLASH_CONTINUE = '.*splash_continue.*'
    MISSING_APP_RETRY = '.*missing_app_retry.*'


def create_next_step(start, end):
    params = { **_AUTH_PARAMS }

    params['start_uri'] = start
    params['end_uri_regex'] = end

    return NextStep('web_session', params)
