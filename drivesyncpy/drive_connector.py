class DriveConnector(object):
    def upload_file(self, filepath):
        raise NotImplementedError()

    def delete_file(self, filepath):
        raise NotImplementedError()

    def update_file(self, filepath):
        raise NotImplementedError()

    def move_file(self, filepath):
        raise NotImplementedError()

    def download_file(self, file_id):
        raise NotImplementedError()

    def create_dir(self, dirpath):
        raise NotImplementedError()

    def delete_dir(self, dirpath):
        raise NotImplementedError()

    def update_dir(self, dirpath):
        raise NotImplementedError()

    def move_dir(self, filepath):
        raise NotImplementedError()

    def download_dir(self, dirpaht):
        raise NotImplementedError()
