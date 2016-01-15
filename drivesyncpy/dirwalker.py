from os import walk
from os.path import join, relpath, abspath, basename
from collections import OrderedDict

from util import UpSyncFile, UpSyncDir


class DirWalker(object):
    def __init__(self, root_dir):
        self._root_dir = abspath(root_dir)
        self._rel_root = basename(root_dir)
        self.paths = OrderedDict()
        self.walk()

    def walk(self):
        self.paths[self._rel_root] = UpSyncDir(self._rel_root)

        for path, dirs, files in walk(self._root_dir):
            self._walk_dirs(path, dirs)

            parent_dir = self._relpath(path)
            parent = self.paths[parent_dir]
            parent.children = [UpSyncFile(join(parent_dir, f)) for f in files]

    def _walk_dirs(self, path, dirs):
        for d in dirs:
            dir_path = self._relpath(join(path, d))
            self.paths[dir_path] = UpSyncDir(dir_path)

    def _relpath(self, path):
        if path == self._root_dir:
            return self._rel_root
        return join(self._rel_root, relpath(path, self._root_dir))
