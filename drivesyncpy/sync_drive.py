import sys

import pyinotify

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
        if event.dir:
            self._wm.add_watch(event.pathname, INOTIFY_EVENT_MASK)
            self._dc.upload_dir(event.pathname)
        else:
            self._dc.upload_file(event.pathname)

    def process_IN_DELETE(self, event):
        print("IN_DELETE {}".format(event))
        self._dc.delete_file(event.pathname)

    def process_IN_MOVED_FROM(self, event):
        print("MOVED FROM {}".format(event))

    def process_IN_MOVED_TO(self, event):
        if hasattr(event, "src_pathname"):
            print("MOVED TO: {} with {}".format(event.src_pathname, event))
        else:
            print("create new {}".format(event))
            self._dc.upload_file(event.pathname)

    def process_default(self, event):
        print("Default Event: {}".format(event))


def sync_drive(root_dir):
    wm = pyinotify.WatchManager()
    dc = GDriveConnector(root_dir)
    event_handler = UpSyncWatcher(watch_manager=wm, drive_connector=dc)

    notifier = pyinotify.Notifier(wm, default_proc_fun=event_handler)
    wm.add_watch(root_dir, INOTIFY_EVENT_MASK)
    notifier.loop()


if __name__ == "__main__":
    sync_drive(sys.argv[1])
