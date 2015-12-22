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
        self._initialized = False
        self._collect_ids('0B42oFDXxUu3aUlZmLVpZaGFOMms')

    def upload_file(self, file_path):
        file_obj = self._create_new_file(file_path)
        file_obj.Upload()

    def delete_file(self, file_path):
        file_obj = self.drive.CreateFile({'id': self._paths[file_path]})
        self._trash_file(file_obj)

    def update_file(self, file_path):
        pass

    def move_file(self, file_path):
        pass

    def download_file(self, file_id):
        pass

    def upload_dir(self, dir_path):
        file_obj = self._create_new_file(dir_path, is_dir=True)
        file_obj.Upload()

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
        self._initialized = True
        print("Collected {} files from {}".format(len(self._ids),
                                                  self._ids[root_folder]))

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
        return {"parents": [{"kind": "drive#fileLink", "id": parent}]}

    def _create_new_file(self, file_path, is_dir=False):
        metadata = self._get_parent_metadata(file_path)
        file_obj = self.drive.CreateFile(metadata)
        file_obj['title'] = path.basename(file_path)

        if is_dir:
            file_obj['mimeType'] = DRIVE_FOLDER
        else:
            file_obj.SetContentFile(file_path)

        return file_obj
