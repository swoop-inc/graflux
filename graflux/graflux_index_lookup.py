import requests

from graphite_api.config import logger

log = logger


class GrafluxIndexLookup(object):
    def __init__(self, config):
        self.config = config.get('index', {})
        self.indexer_url = self.config.get('index_url', 'http://localhost:8080/find')

    def query(self, query):
        r = requests.get(self.indexer_url, params={'q': query})
        return r.json()
