from os import stat
from stat import ST_CTIME
from datetime import datetime, timezone, timedelta

GOOGLE_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


def convert_google_time(google_time):
    dt_unawre = datetime.strptime(google_time, GOOGLE_TIME_FORMAT)
    dt = dt_unawre.replace(tzinfo=timezone.utc)
    delta = dt - datetime(1970, 1, 1, tzinfo=timezone.utc)
    return delta / timedelta(seconds=1)


class _File(object):
    def __init__(self, path):
        self.path = path
        self.last_modified = None


# Up - Represent local files
class UpSyncFile(_File):
    def __init__(self, path):
        super(UpSyncFile, self).__init__(path)
        self.last_modified = stat(path)[ST_CTIME]


class UpSyncDir(UpSyncFile):
    def __init__(self, path):
        super(UpSyncDir, self).__init__(path)
        self.children = []


# Down - Represent Google Drive files
class DownSyncFile(_File):
    def __init__(self, path, last_mod, file_id):
        super(DownSyncFile, self).__init__(path)
        self.last_modified = convert_google_time(last_mod)
        self.file_id = file_id


class DownSyncDir(DownSyncFile):
    def __init__(self, path, last_mod, file_id):
        super(DownSyncDir, self).__init__(path, last_mod, file_id)
        self.children = []
