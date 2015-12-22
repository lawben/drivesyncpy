from os import path
from Queue import Queue

from pydrive.drive import GoogleDrive

from drive_connector import DriveConnector
from drive_auth import get_google_auth

DRIVE_FOLDER = "application/vnd.google-apps.folder"


class GDriveConnector(DriveConnector):
    def __init__(self, root):
        self.gauth = get_google_auth()
        self.drive = GoogleDrive(self.gauth)
        self._root = root
        self._paths = {}
        self._ids = {}

    def upload_file(self, filepath):
        file_obj = self.drive.CreateFile()
        file_obj.SetContentFile(filepath)
        file_obj.Upload()

    def delete_file(self, filepath):
        file_obj = self.drive.CreateFile({'id': self._paths[filepath]})
        self._trash_file(file_obj)

    def update_file(self, filepath):
        pass

    def move_file(self, filepath):
        pass

    def download_file(self, file_id):
        pass

    def _trash_file(self, file_obj, param=None):
        # Temporary workaround until delete is merged
        if param is None:
            param = {}
        param['fileId'] = self.metadata.get('id')
        try:
            file_obj.auth.service.files().trash(**param).execute()
        except Exception, e:
            raise Exception("Deleting error {}".format(e))

    def _collect_ids(self, root_folder=None):
        folders = Queue()
        if root_folder is None:
            folders.put('root')
        else:
            folders.put(root_folder)

        self._cache_path_id(self.drive.CreateFile({'id': root_folder}))
        self._traverse_files(folders)

    def _query_folder_children(self, query, folder_id):
        new_folders = []
        for f in self.drive.ListFile({'q': query}).GetList():
            self._cache_path_id(f)
            if f['mimeType'] == DRIVE_FOLDER:
                new_folders.append(f['id'])
        return new_folders

    def _traverse_files(self, folders):
        query = "'{folder}' in parents and trashed=false"
        while not folders.empty():
            folder = folders.get()
            q = query.format(folder=folder)
            new_folders = self._query_folder_children(q, folder)
            for f in new_folders:
                folders.put(f)

    def _join_parent_chain(self, file_obj):
        parent = file_obj['parents'][0]
        if parent['isRoot']:
            rel_path = file_obj['title']
        else:
            parent_id = parent['id']
            rel_path = path.join(self._ids[parent_id], file_obj['title'])
        return path.join(self._root, rel_path)

    def _cache_path_id(self, file_obj):
        file_id = file_obj['id']
        parent_chain = self._join_parent_chain(file_obj)
        self._ids[file_id] = parent_chain
        self._paths[parent_chain] = file_id


dc = GDriveConnector("foobar")
# dc.get_files("hacks")
dc._collect_ids('0B42oFDXxUu3aUlZmLVpZaGFOMms')
print dc._ids
print dc._paths
