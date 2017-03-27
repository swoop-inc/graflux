import time

from .graflux_index_lookup import GrafluxIndexLookup
from graphite_api.intervals import Interval, IntervalSet
from graphite_api.node import LeafNode, BranchNode
from .query_engine import QueryEngine


class InfluxDBLeafNode(LeafNode):
    __fetch_multi__ = 'influxDB'


class InfluxDBReader(object):
    __slots__ = ('path', 'query_engine')

    def __init__(self, path, query_engine):
        self.path = path
        self.query_engine = query_engine

    def fetch(self, start_time, end_time):
        data = self.query_engine.query([self.path], start_time, end_time)

        time_info = data['from'], data['to'], data['step']
        return time_info, data['series'].get(self.path, [])

    def get_intervals(self):
        return IntervalSet([Interval(0, int(time.time()))])


class InfluxDBFinder(object):
    __fetch_multi__ = 'influxDB'

    def __init__(self, config=None):
        self.config = config.get('graflux', {})

        self.query_engine = QueryEngine(self.config)
        self.metric_lookup = GrafluxIndexLookup(self.config)
        # self.metric_lookup = MetricLookup(self.config)
        # self.metric_lookup.start_background_refresh()

    def find_nodes(self, query):
        paths = self.metric_lookup.query(query.pattern)

        for path in paths:
            if path['is_leaf']:
                yield InfluxDBLeafNode(path['metric'], InfluxDBReader(path['metric'], self.query_engine))
            else:
                yield BranchNode(path['metric'])

    def fetch_multi(self, nodes, start_time, end_time):
        paths = [node.path for node in nodes]
        data = self.query_engine.query(paths, start_time, end_time)

        time_info = data['from'], data['to'], data['step']
        return time_info, data['series']
