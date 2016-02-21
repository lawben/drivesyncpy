from re import findall
from queue import Queue
from os.path import join, basename, dirname
from drive_auth import get_google_auth
from collections import OrderedDict

from pydrive.drive import GoogleDrive
from pydrive.files import FileNotDownloadableError

from util import DownSyncFile, DownSyncDir, make_dir

DRIVE_FOLDER = "application/vnd.google-apps.folder"


class GDriveConnector:
    def __init__(self, root):
        self.paths = OrderedDict()
        self._gauth = get_google_auth()
        self._service = self._gauth.service
        self._drive = GoogleDrive(self._gauth)
        self._root = root
        self._rel_root = basename(root)
        self._ids = {}
        # self._walk_remote('0B42oFDXxUu3aUlZmLVpZaGFOMms')
        self._walk_remote()
        # print self._get_changes()

    def upload(self, up_obj):
        path = up_obj.path
        if up_obj.is_dir:
            self.upload_dir(path)
        else:
            self.upload_file(path)

    def update(self, up_obj):
        path = up_obj.path
        if not up_obj.is_dir:
            # TODO: Change to update
            self.update_file(path)

    def download(self, down_obj):
        f_id = down_obj.file_id
        if down_obj.is_dir:
            self.download_dir(f_id)
        else:
            self.download_file(f_id)

    def move(self, sync_obj):
        pass

    def delete(self, sync_obj):
        pass

    def upload_file(self, file_path):
        file_obj = self._create_file(file_path)
        file_obj.Upload()
        self._cache_path(file_obj)

    def delete_file(self, file_path):
        file_obj = self._file_by_id(self.paths[file_path].file_id)
        self._trash_file(file_obj)

    def update_file(self, file_path):
        file_obj = self._file_by_id(self.paths[file_path].file_id)
        file_obj.SetContentFile(file_path)
        file_obj.Upload()

    def move_file(self, file_path):
        pass

    def download_file(self, file_id):
        file_obj = self._file_by_id(file_id)
        self._cache_path(file_obj)
        file_path = self._ids[file_id]
        try:
            file_obj.GetContentFile(file_path)
        except FileNotDownloadableError:
            if not self._download_best_match(file_obj, file_path):
                raise

    def upload_dir(self, dir_path):
        file_obj = self._create_file(dir_path, is_dir=True)
        file_obj.Upload()
        self._cache_path(file_obj, is_dir=True)

    def download_dir(self, dir_id):
        self._cache_path(self._file_by_id(dir_id), is_dir=True)
        file_path = self._ids[dir_id]
        make_dir(file_path)

    def _trash_file(self, file_obj, param=None):
        # Temporary workaround until delete is merged
        if param is None:
            param = {}
        param['fileId'] = file_obj['id']
        try:
            self._service.files().trash(**param).execute()
        except Exception as e:
            raise Exception("Deleting error: {}".format(e))

    def _walk_remote(self, root_folder='root'):
        folders = Queue()
        folders.put(root_folder)

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
                self._cache_path(f, is_dir=True)
                yield f_id
            else:
                self._cache_path(f)

    def _traverse_files(self, folders):
        # TODO: get only own files, not shared
        query = "'{folder}' in parents and trashed=false"
        count = 0
        while not folders.empty():
            folder = folders.get()
            q = query.format(folder=folder)
            for f in self._query_folder_children(q):
                folders.put(f)
            count += 1
            if count == 2:
                return

    def _join_parent_chain(self, file_obj):
        # Catch root folder
        try:
            parent = file_obj['parents'][0]
        except IndexError:
            return self._rel_root

        pre_path = self._rel_root
        if not parent['isRoot']:
            pre_path = self._ids[parent['id']]

        title = file_obj['title'].replace("/", "_")
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
        try:
            parent_obj = self.paths[parent_path]
            parent = parent_obj.file_id
        except KeyError:
            parent = 'root'

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

    def _download_best_match(self, file_obj, path):
        mimetype = file_obj.metadata.get("mimeType")
        export_links = file_obj.metadata.get("exportLinks")
        best_match = [0, None]
        for mt in export_links.keys():
            match = self._calc_mimetype_similarity(mimetype, mt)
            if match > best_match[0]:
                best_match = [match, mt]

        file_obj.metadata['downloadUrl'] = export_links[best_match[1]]
        try:
            file_obj.GetContentFile(path)
            return True
        except FileNotDownloadableError:
            return False

    def _calc_mimetype_similarity(self, mimetype, other):
        mt_words = self._tokenize(mimetype)
        other_words = self._tokenize(other)
        same = len(mt_words.intersection(other_words))
        total = len(mt_words.union(other_words))
        return same / total

    def _tokenize(self, string):
        return set(findall(r'[\w]+', string))