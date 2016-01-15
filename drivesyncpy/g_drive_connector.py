from os import path, makedirs
from Queue import Queue

from pydrive.drive import GoogleDrive

from drive_connector import DriveConnector
from drive_auth import get_google_auth

DRIVE_FOLDER = "application/vnd.google-apps.folder"


class GDriveConnector(DriveConnector):
    def __init__(self, root):
        self._gauth = get_google_auth()
        self._service = self._gauth.service
        self._drive = GoogleDrive(self._gauth)
        self._root = root
        self._paths = {}
        self._ids = {}
        # print self._get_changes()

    def upload_file(self, file_path):
        file_obj = self._create_file(file_path)
        file_obj.Upload()

    def delete_file(self, file_path):
        file_obj = self._drive.CreateFile({'id': self._paths[file_path]})
        self._trash_file(file_obj)

    def update_file(self, file_path):
        pass

    def move_file(self, file_path):
        pass

    def download_file(self, file_id):
        file_obj = self._drive.CreateFile({'id': file_id})
        self._cache_path_id(file_obj)
        file_path = self._ids[file_id]
        file_obj.GetContentFile(file_path)

    def upload_dir(self, dir_path):
        file_obj = self._create_file(dir_path, is_dir=True)
        file_obj.Upload()

    def download_dir(self, dir_id):
        self._cache_path_id(self._drive.CreateFile({'id': dir_id}))
        file_path = self._ids[dir_id]
        makedirs(file_path)

    def _trash_file(self, file_obj, param=None):
        # Temporary workaround until delete is merged
        if param is None:
            param = {}
        param['fileId'] = file_obj['id']
        try:
            file_obj.auth.service.files().trash(**param).execute()
        except Exception, e:
            raise Exception("Deleting error: {}".format(e))

    def _down_sync(self, root_folder='root'):
        folders = Queue()
        folders.put(root_folder)

        # self.download_dir(root_folder)
        self._traverse_files(folders)
        self._initialized = True
        print("Collected {} files from {}".format(len(self._ids),
                                                  self._ids[root_folder]))

    def _get_changes(self, params=None):
        # self._down_sync('0B42oFDXxUu3aUlZmLVpZaGFOMms')
        changes = []
        if params is None:
            params = {'pageToken': 693622}

        params['includeSubscribed'] = False
        return self._service.changes().list(**params).execute()

    def _query_folder_children(self, query, folder_id):
        new_folders = []
        for f in self._drive.ListFile({'q': query}).GetList():
            f_id = f['id']
            if f['mimeType'] == DRIVE_FOLDER:
                # self.download_dir(f_id)
                new_folders.append(f_id)
            else:
                # self.download_file(f_id)
                pass
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
        pre_path = self._root
        if not parent['isRoot']:
            pre_path = self._ids[parent['id']]
        return path.join(pre_path, file_obj['title'])

    def _cache_path_id(self, file_obj):
        file_id = file_obj['id']
        parent_chain = self._join_parent_chain(file_obj)
        self._ids[file_id] = parent_chain
        self._paths[parent_chain] = file_id

    def _get_parent_metadata(self, file_path):
        parent_path = path.dirname(file_path)
        parent = self._paths.get(parent_path, 'root')
        return {"parents": [{"kind": "drive#parentReference", "id": parent}]}

    def _create_file(self, file_path, is_dir=False):
        metadata = self._get_parent_metadata(file_path)
        file_obj = self._drive.CreateFile(metadata)
        file_obj['title'] = path.basename(file_path)

        if is_dir:
            file_obj['mimeType'] = DRIVE_FOLDER
        else:
            file_obj.SetContentFile(file_path)

        return file_obj
