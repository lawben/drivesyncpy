from pydrive.auth import GoogleAuth


SETTINGS_PATH = "oauth/settings.yaml"


def get_google_auth():
    gauth = GoogleAuth(settings_file=SETTINGS_PATH)
    gauth.LoadCredentials()

    if gauth.credentials is None:
        gauth.LocalWebserverAuth()
    elif gauth.access_token_expired:
        gauth.Refresh()
    else:
        gauth.Authorize()

    gauth.SaveCredentials()
    return gauth