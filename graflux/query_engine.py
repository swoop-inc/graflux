from influxdb import InfluxDBClient
from collections import OrderedDict

import re


# TODO makes sense to abstract this to allow cacheable wrapper implementations
class QueryEngine(object):
    def __init__(self, config):
        influx_config = config.get('influxdb', {})
        self.client = InfluxDBClient(influx_config.get('host', 'localhost'),
                                     influx_config.get('port', '8086'),
                                     influx_config.get('user', 'root'),
                                     influx_config.get('password', 'root'),
                                     influx_config.get('db', 'graphite'),
                                     influx_config.get('ssl', 'false'))

        self.config = config
        self.aggregate_dict = None
        self.steps = config.get('steps', {})

    def query(self, metrics, start_time, end_time):
        step = self.determine_interval(start_time, end_time)

        query_sets = self.build_query_sets(metrics)

        result = {
            'series': {},
            'from': start_time,
            'to': end_time,
            'step': step
        }

        for agg, metrics in query_sets.items():
            series_list = ', '.join(['"%s"' % path for path in metrics])
            influx_query = self.build_influx_query(series_list, start_time, end_time, agg, step)
            data = self.client.query(influx_query, {'epoch': 's'})
            for key in data.keys():
                result['series'][key[0]] = [d['value'] for d in data.get_points(key[0])]

        return result

    def show_series(self):
        data = self.client.query('SHOW SERIES')
        return (r['name'] for r in data.raw['series']) if 'series' in data.raw else []

    # Private

    def build_aggregate_dict(self):
        self.aggregate_dict = OrderedDict(
            (re.compile(reg), agg) for (reg, agg) in self.config.get('aggregates', [])
        )

    def lookup_aggregate(self, metric):
        if not self.aggregate_dict:
            self.build_aggregate_dict()

        for regex, agg in self.aggregate_dict.items():
            if regex.search(metric): return agg

        return 'mean'  # TODO: make default configurable

    def build_query_sets(self, metrics):
        query_sets = {}
        for metric in metrics:
            agg = self.lookup_aggregate(metric)
            if agg not in query_sets: query_sets[agg] = []
            query_sets[agg].append(metric)

        return query_sets

    def determine_interval(self, start_time, end_time):
        span = end_time - start_time

        final_step = 60  # TODO make configurable, should match minimum data resolution

        for limit, step in self.steps:
            if span >= limit and step > final_step:
                final_step = step
            else:
                break

        return final_step

    def build_influx_query(self, metrics, start_time, end_time, agg='mean', interval=300):
        return 'SELECT %s(value) AS value FROM %s WHERE time > %ds AND time <= %ds GROUP BY time(%ss)' % (agg, metrics, start_time, end_time, interval)
