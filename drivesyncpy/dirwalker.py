from os import walk, stat
from stat import ST_CTIME
from os.path import join, relpath, abspath, basename


class _File(object):
    __slots__ = ['path', 'last_modified']

    def __init__(self, path):
        self.path = path
        self.last_modified = stat(path)[ST_CTIME]

    def is_dir(self):
        return False


class _Dir(_File):
    __slots__ = ['path', 'last_modified', 'children']

    def __init__(self, path):
        super(self.__class__, self).__init__(path)
        self.children = []

    def is_dir(self):
        return True


class DirWalker(object):
    def __init__(self, root_dir):
        self._root_dir = abspath(root_dir)
        self._rel_root = basename(root_dir)
        self.paths = {}
        self.walk()

    def walk(self):
        self.paths[self._rel_root] = _Dir(self._rel_root)

        for path, dirs, files in walk(self._root_dir):
            self._walk_dirs(path, dirs)

            parent_dir = self._relpath(path)
            parent = self.paths[parent_dir]
            parent.children = [_File(join(parent_dir, f)) for f in files]

    def _walk_dirs(self, path, dirs):
        for d in dirs:
            dir_path = self._relpath(join(path, d))
            self.paths[dir_path] = _Dir(dir_path)

    def _relpath(self, path):
        if path == self._root_dir:
            return self._rel_root
        return join(self._rel_root, relpath(path, self._root_dir))
