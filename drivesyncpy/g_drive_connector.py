from os import makedirs
from Queue import Queue
from os.path import join, basename, dirname
from collections import OrderedDict

from pydrive.drive import GoogleDrive

from util import DownSyncFile, DownSyncDir
from drive_auth import get_google_auth
from drive_connector import DriveConnector

DRIVE_FOLDER = "application/vnd.google-apps.folder"


class GDriveConnector(DriveConnector):
    def __init__(self, root):
        self.paths = OrderedDict()
        self._gauth = get_google_auth()
        self._service = self._gauth.service
        self._drive = GoogleDrive(self._gauth)
        self._root = root
        self._rel_root = basename(root)
        self._ids = {}
        # self._down_sync('0B42oFDXxUu3aUlZmLVpZaGFOMms')
        self._down_sync()
        # print self._get_changes()

    def upload_file(self, file_path):
        file_obj = self._create_file(file_path)
        file_obj.Upload()

    def delete_file(self, file_path):
        file_obj = self._file_by_id(self.paths[file_path])
        self._trash_file(file_obj)

    def update_file(self, file_path):
        pass

    def move_file(self, file_path):
        pass

    def download_file(self, file_id):
        file_obj = self._file_by_id(file_id)
        self._cache_path(file_obj)
        file_path = self._ids[file_id]
        file_obj.GetContentFile(file_path)

    def upload_dir(self, dir_path):
        file_obj = self._create_file(dir_path, is_dir=True)
        file_obj.Upload()

    def download_dir(self, dir_id):
        self._cache_path(self._file_by_id(dir_id))
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
        self._cache_path(self._file_by_id(root_folder), is_dir=True)
        self._traverse_files(folders)
        self._initialized = True
        print("Collected {} files from {}".format(len(self._ids),
                                                  self._ids[root_folder]))

    def _get_changes(self, params=None):
        if params is None:
            params = {'pageToken': 693622}

        params['includeSubscribed'] = False
        return self._service.changes().list(**params).execute()

    def _query_folder_children(self, query):
        for f in self._drive.ListFile({'q': query}).GetList():
            f_id = f['id']
            if f['mimeType'] == DRIVE_FOLDER:
                # self.download_dir(f_id)
                self._cache_path(f, is_dir=True)
                yield f_id
            else:
                # self.download_file(f_id)
                self._cache_path(f)
                pass

    def _traverse_files(self, folders):
        # TODO: get only own files, not shared
        query = "'{folder}' in parents and trashed=false"
        while not folders.empty():
            folder = folders.get()
            q = query.format(folder=folder)
            for f in self._query_folder_children(q):
                folders.put(f)

    def _join_parent_chain(self, file_obj):
        # Catch root folder
        try:
            parent = file_obj['parents'][0]
        except IndexError:
            return self._rel_root

        pre_path = self._rel_root
        if not parent['isRoot']:
            pre_path = self._ids[parent['id']]

        # TODO: Fix '/' in file name BP N2 idealo/Learning Spark / Flink
        title = file_obj['title'].replace("/", "\/")
        return join(pre_path, title)

    def _cache_path(self, file_obj, is_dir=False):
        file_id = file_obj['id']
        parent_chain = self._join_parent_chain(file_obj)
        self._ids[file_id] = parent_chain
        last_mod = file_obj['modifiedDate']
        file_info = (parent_chain, last_mod, file_id)

        if is_dir:
            down_sync = DownSyncDir(*file_info)
        else:
            down_sync = DownSyncFile(*file_info)
            parent = self.paths[dirname(parent_chain)]
            parent.children.append(down_sync)

        self.paths[parent_chain] = down_sync

    def _get_parent_metadata(self, file_path):
        parent_path = dirname(file_path)
        parent = self.paths.get(parent_path, 'root')
        return {"parents": [{"kind": "drive#parentReference", "id": parent}]}

    def _create_file(self, file_path, is_dir=False):
        metadata = self._get_parent_metadata(file_path)
        file_obj = self._drive.CreateFile(metadata)
        file_obj['title'] = basename(file_path)

        if is_dir:
            file_obj['mimeType'] = DRIVE_FOLDER
        else:
            file_obj.SetContentFile(file_path)

        return file_obj

    def _file_by_id(self, file_id):
        return self._drive.CreateFile({'id': file_id})