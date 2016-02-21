import sys
from os.path import abspath, join, relpath, basename

import pyinotify

from dirwalker import DirWalker
from g_drive_connector import GDriveConnector
from util import merge_upload, merge_download, make_dir


INOTIFY_EVENT_MASK = pyinotify.IN_CREATE | pyinotify.IN_MODIFY | \
                     pyinotify.IN_DELETE | pyinotify.IN_MOVED_FROM | \
                     pyinotify.IN_MOVED_TO


class UpSyncWatcher(pyinotify.ProcessEvent):
    def my_init(self, root, watch_manager, drive_connector):
        self._root = root
        self._base_root = basename(root)
        self._wm = watch_manager
        self._dc = drive_connector

    def _relpath(self, path):
        return join(self._base_root, relpath(path, self._root))

    def process_IN_MODIFY(self, event):
        print("IN_MODIFY {}".format(event))
        file_path = self._relpath(event.pathname)
        self._dc.upload_file(file_path)

    def process_IN_CREATE(self, event):
        print("IN_CREATE {}".format(event))
        file_path = self._relpath(event.pathname)
        if event.dir:
            self._wm.add_watch(event.pathname, INOTIFY_EVENT_MASK)
            self._dc.upload_dir(file_path)
            print(self._wm.watches)
        else:
            self._dc.upload_file(file_path)

    def process_IN_DELETE(self, event):
        print("IN_DELETE {}".format(event))
        file_path = self._relpath(event.pathname)
        self._dc.delete_file(file_path)

    def process_IN_MOVED_FROM(self, event):
        print("MOVED FROM {}".format(event))

    def process_IN_MOVED_TO(self, event):
        file_path = self._relpath(event.pathname)
        if hasattr(event, "src_pathname"):
            print("MOVED TO: {} with {}".format(event.src_pathname, event))
        else:
            print("create new {}".format(event))
            self._dc.upload_file(file_path)


def merge_systems(up_files, down_files, drive_connector):
    remote_files = merge_upload(up_files, down_files, drive_connector)
    merge_download(remote_files, drive_connector)


def check_main_stop(notifier):
    """Call after notifier timeout or processed event
       to check if the program should terminate.
    """
    pass


def sync_drive(root_dir):
    wm = pyinotify.WatchManager()
    dc = GDriveConnector(root_dir)
    down_files = dc.paths.copy()
    walker = DirWalker(root_dir)
    up_files = walker.paths
    # merge_systems(up_files, down_files, dc)

    event_handler = UpSyncWatcher(root=root_dir, watch_manager=wm,
                                  drive_connector=dc)

    notifier = pyinotify.Notifier(wm, default_proc_fun=event_handler,
                                  timeout=1000)
    wm.add_watch(root_dir, INOTIFY_EVENT_MASK)
    notifier.loop(callback=check_main_stop)


if __name__ == "__main__":
    root_ = abspath(sys.argv[1])
    make_dir(root_)
    sync_drive(root_)
