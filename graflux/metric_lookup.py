from threading import Timer

from .utils import timed_log
from .query_engine import QueryEngine
from .index_storage import FileStorage
from .metric_index import MetricIndex

from graphite_api.config import logger

log = logger


# TODO support configurable storage system (redis/memcached/file)
class MetricLookup(object):
    def __init__(self, config):
        self.config = config
        self.index_config = config.get('index', {})

        self.build_interval = self.index_config.get('build_interval', 900)
        self.load_interval = self.index_config.get('load_interval', 300)
        self.background_workers_active = False

        self.index = MetricIndex()
        self.storage = FileStorage(self.index_config)

    def query(self, query):
        return self.index.query(query)

    def delete_index(self):
        # TODO possible race with a background load/build here, but this method is largely for test usage
        self.storage.delete_index()
        self.index = MetricIndex()

    # Starts two threads, one to periodically build a new index and one to periodically load the index from storage
    # replacing the existing index.
    def start_background_refresh(self):
        if self.background_workers_active:
            raise StandardError

        log.info('index.background.threads_start')
        self.background_workers_active = True

        # Start threads nearly immediately on initial startup
        Timer(1, self.periodic_build_index).start()
        Timer(1, self.periodic_load_index).start()

    def stop_background_refresh(self):
        log.info('index.background.threads_stop')
        self.background_workers_active = False

    # Wrapper to ensure rescheduling
    def periodic_load_index(self):
        log.info('index.background.load')

        try:
            self.load_index()
        except Exception as e:
            log.error('index.background.load.failure', exception=e)

        if self.background_workers_active:
            Timer(self.load_interval, self.periodic_load_index).start()

    # Wrapper to ensure rescheduling
    def periodic_build_index(self):
        log.info('index.background.build')

        try:
            self.build_index()
        except Exception as e:
            log.info('index.background.build.failure', exception=e)

        if self.background_workers_active:
            Timer(self.build_interval, self.periodic_build_index).start()

    # This method may be run in a separate thread don't use anything with unclear thread safety
    @timed_log('index.load')
    def load_index(self):
        log.info('index.load.start')

        data = FileStorage(self.index_config).read()
        if data:
            # TODO verify that simple variable reassignment is actually threadsafe in python, I think the GIL defends it
            self.index = MetricIndex.from_json(data)
        else:
            log.info('index.load.not_found')

    # This method may be run in a separate thread don't use anything with unclear thread safety
    @timed_log('index.build')
    def build_index(self):
        log.info('index.build.start')

        storage = FileStorage(self.index_config)
        query_engine = QueryEngine(self.config)

        if storage.try_acquire_update_lock():
            log.info('index.build.lock_acquired')

            data = query_engine.show_series()

            index = MetricIndex()
            for metric in data:
                index.insert(metric)

            log.info('index.build.serializing')
            storage.save(index.to_json())

            storage.release_update_lock()
        else:
            log.info('index.build.lock_unavailable')
