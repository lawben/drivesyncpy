from os import stat
from stat import ST_CTIME
from datetime import datetime, timezone, timedelta

GOOGLE_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


def convert_google_time(google_time):
    dt_unawre = datetime.strptime(google_time, GOOGLE_TIME_FORMAT)
    dt = dt_unawre.replace(tzinfo=timezone.utc)
    delta = dt - datetime(1970, 1, 1, tzinfo=timezone.utc)
    return delta // timedelta(seconds=1)


def merge_upload(up_files, down_files, drive_connector):
    seen = set()
    for path, up_f in up_files.items():
        if path in down_files:
            down_f = down_files[path]
            seen.add(down_f.path)
            if up_f.is_newer(down_f):
                print("Updating: {}".format(up_f))
                drive_connector.update(up_f)
            else:
                print("Downloading: {}".format(up_f))
                drive_connector.download(down_f)
        else:
            print("Uploading: {}".format(up_f))
            drive_connector.upload(up_f)
    return {key: val for key, val in down_files.items() if key not in seen}


def merge_download(down_files, drive_connector):
    for path, down_f in down_files.items():
        drive_connector.download(down_f)


class _File:
    def __init__(self, path):
        self.path = path
        self.last_modified = None
        self.is_dir = False

    def is_newer(self, other_file):
        return self.last_modified > other_file.last_modified

    def __str__(self):
        string = "<{}(path={}, last_mod={}, is_dir={})>"
        return string.format(self.__class__.__name__, self.path,
                             self.last_modified, self.is_dir)


# Up - Represent local files
class UpSyncFile(_File):
    def __init__(self, path):
        super().__init__(path)
        self.last_modified = stat(path)[ST_CTIME]
        self.is_local = True


class UpSyncDir(UpSyncFile):
    def __init__(self, path):
        super().__init__(path)
        self.children = []
        self.is_dir = True


# Down - Represent Google Drive files
class DownSyncFile(_File):
    def __init__(self, path, last_mod, file_id):
        super().__init__(path)
        self.last_modified = convert_google_time(last_mod)
        self.file_id = file_id
        self.is_local = False


class DownSyncDir(DownSyncFile):
    def __init__(self, path, last_mod, file_id):
        super().__init__(path, last_mod, file_id)
        self.children = []
        self.is_dir = True
