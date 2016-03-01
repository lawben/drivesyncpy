from os import path

from pydrive.auth import GoogleAuth, AuthError


SETTINGS_PATH = path.join(path.dirname(__file__), "oauth/settings.yaml")


def get_google_auth():
    tries = 0
    while tries < 3:
        g_auth = _authenticate()
        if g_auth.service is not None:
            return g_auth
        tries += 1

    raise AuthError("Could not authenticate after 3 tries!")


def _authenticate():
    g_auth = GoogleAuth(settings_file=SETTINGS_PATH)
    g_auth.LoadCredentials()

    if g_auth.credentials is None:
        g_auth.LocalWebserverAuth()
    elif g_auth.access_token_expired:
        g_auth.Refresh()
    else:
        g_auth.Authorize()

    g_auth.SaveCredentials()
    return g_auth
