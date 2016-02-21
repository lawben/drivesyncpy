from stat import ST_CTIME
from os import stat, makedirs
from datetime import datetime, timezone, timedelta

GOOGLE_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


def convert_google_time(google_time):
    dt_unaware = datetime.strptime(google_time, GOOGLE_TIME_FORMAT)
    dt = dt_unaware.replace(tzinfo=timezone.utc)
    delta = dt - datetime(1970, 1, 1, tzinfo=timezone.utc)
    return delta // timedelta(seconds=1)


def flatten_paths(up_files):
    dirs = list(up_files.items())
    files = [(c.path, c) for _, f in up_files.items() for c in f.children]
    return dirs + files


def merge_upload(up_dirs, down_files, drive_connector):
    up_files = flatten_paths(up_dirs)
    seen = set()
    for path, up_f in up_files:
        if path in down_files:
            down_f = down_files[path]
            seen.add(down_f.path)
            chose_file(up_f, down_f, drive_connector)
        else:
            print("Uploading: {}".format(up_f))
            drive_connector.upload(up_f)
    return {key: val for key, val in down_files.items() if key not in seen}


def chose_file(up_f, down_f, dc):
    if up_f.is_newer(down_f):
        print("Updating: {}".format(up_f))
        dc.update(up_f)
    else:
        print("Downloading newer: {}".format(up_f))
        dc.download(down_f)


def merge_download(down_files, drive_connector):
    for path, down_f in down_files.items():
        print("Downloading: {}".format(down_f))
        drive_connector.download(down_f)


def make_dir(file_path):
    try:
        makedirs(file_path)
    except FileExistsError:
        pass
    except OSError:
        print("error while creating dir {}".format(file_path))


class _File:
    def __init__(self, path):
        self.path = path
        self.last_modified = None
        self.is_dir = False

    def is_newer(self, other_file):
        return self.last_modified >= other_file.last_modified

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
