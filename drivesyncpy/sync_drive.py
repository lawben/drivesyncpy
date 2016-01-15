import sys
from os.path import abspath

import pyinotify

from dirwalker import DirWalker
from g_drive_connector import GDriveConnector


INOTIFY_EVENT_MASK = pyinotify.IN_CREATE | pyinotify.IN_MODIFY | \
                     pyinotify.IN_DELETE | pyinotify.IN_MOVED_FROM | \
                     pyinotify.IN_MOVED_TO


class UpSyncWatcher(pyinotify.ProcessEvent):
    def my_init(self, watch_manager, drive_connector):
        self._wm = watch_manager
        self._dc = drive_connector

    def process_IN_MODIFY(self, event):
        print("IN_MODIFY {}".format(event))
        # self._dc.upload_file(event.pathname)

    def process_IN_CREATE(self, event):
        print("IN_CREATE {}".format(event))
        file_path = event.pathname
        if event.dir:
            self._wm.add_watch(file_path, INOTIFY_EVENT_MASK)
            self._dc.upload_dir(file_path)
        else:
            self._dc.upload_file(file_path)

    def process_IN_DELETE(self, event):
        print("IN_DELETE {}".format(event))
        # self._dc.delete_file(event.pathname)

    def process_IN_MOVED_FROM(self, event):
        print("MOVED FROM {}".format(event))

    def process_IN_MOVED_TO(self, event):
        if hasattr(event, "src_pathname"):
            print("MOVED TO: {} with {}".format(event.src_pathname, event))
        else:
            print("create new {}".format(event))
            # self._dc.upload_file(event.pathname)

    def process_default(self, event):
        print("Default Event: {}".format(event))


def sync_drive(root_dir):
    wm = pyinotify.WatchManager()
    dc = GDriveConnector(root_dir)
    down_files = dc.paths
    print down_files
    walker = DirWalker(root_dir)
    up_files = walker.paths
    print up_files
    for path, handle in up_files.iteritems():
        print "dir: ", path, "last mod:", handle.last_modified
        for f in handle.children:
            print "file:", f.path, "last mod:", f.last_modified

    event_handler = UpSyncWatcher(watch_manager=wm, drive_connector=dc)

    notifier = pyinotify.Notifier(wm, default_proc_fun=event_handler)
    wm.add_watch(root_dir, INOTIFY_EVENT_MASK)
    notifier.loop()


if __name__ == "__main__":
    root = abspath(sys.argv[1])
    sync_drive(root)
