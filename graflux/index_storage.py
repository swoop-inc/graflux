import os
import time

from structlog import get_logger

log = get_logger()


# TODO provide memcached / redis implementations to support multi-box graphite-api installs
class FileStorage(object):
    INDEX_FILE_NAME = 'index.json'
    INDEX_TMP_FILE_NAME = 'index.json.new'
    LOCK_FILE_NAME = 'index.lock'
    LOCK_TIMEOUT = 120

    def __init__(self, config):
        self.path = config['path']

    def read(self):
        try:
            with open(self.index_file_path(), 'r') as f:
                return f.read()
        except IOError as e:
            log.error('index.file.read.exception', exception=e)
            return False

    def save(self, data):
        with open(self.index_tmp_file_path(), 'w') as f:
            f.write(data)

        os.rename(self.index_tmp_file_path(), self.index_file_path())

    def try_acquire_update_lock(self):
        lock_path = self.lock_file_path()

        # Check if a lock exists and if it does check for expiration
        try:
            m_time = os.path.getmtime(lock_path)
            if int(time.time()) - m_time >= FileStorage.LOCK_TIMEOUT:
                log.warn('index.file.lock_expired',
                         note="This should not happen. Most likely caused by a crashed or very slow updater process.")
                self.release_update_lock()
            else:
                return False
        except OSError:  # Generally the result of no lock file existing
            pass

        # Attempt to atomically write the lock file
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_RDWR)
            with os.fdopen(fd, 'w') as f:
                f.write(str(os.getpid()))
                return True
        except OSError as e:
            log.warn('index.file.lock_collision',
                     note="Normal if this happens occasionally but should not be common",
                     exception=e)
            return False

    def delete_index(self):
        try:
            os.remove(self.index_file_path())
        except OSError as e:
            # Likely file not present, which is OK, log in case it's permissions or other
            log.warn('index.file.delete_index_file.exception', exception=e)

    def release_update_lock(self):
        try:
            os.remove(self.lock_file_path())
        except OSError as e:
            # Likely file not present, which is OK, log in case it's permissions or other
            log.warn('index.file.delete_lock_file.exception', exception=e)

    def index_file_path(self):
        return os.path.join(self.path, FileStorage.INDEX_FILE_NAME)

    def index_tmp_file_path(self):
        return os.path.join(self.path, FileStorage.INDEX_TMP_FILE_NAME)

    def lock_file_path(self):
        return os.path.join(self.path, FileStorage.LOCK_FILE_NAME)
