import six
import unittest

import time

from graflux.query_engine import QueryEngine

from influxdb import InfluxDBClient
import influxdb.exceptions


class QueryEngineTest(unittest.TestCase):
    def setUp(self):
        self.db = 'graflux_test'
        self.config = {
            'influxdb': {
                'host': 'localhost',
                'port': 8086,
                'db': self.db
            },
            'aggregates': [
                ['.sum$', 'sum'],
                ['.gauge$', 'last'],
                ['.*', 'mean']
            ],
            'steps': [
                [1000, 60],
                [5000, 300],
                [10000, 600]
            ]
        }

        self.client = InfluxDBClient(database=self.db)
        self.query_engine = QueryEngine(self.config)

    def clean_db(self):
        try:
            self.client.drop_database(self.db)
        except influxdb.exceptions.InfluxDBClientError:
            pass
        self.client.create_database(self.db)

    def create_test_data(self, metrics):
        data = [{
                    "measurement": metric,
                    "tags": {},
                    "fields": {
                        "value": 1,
                    }
                }
                for metric in metrics]

        self.assertTrue(self.client.write_points(data))

    def test_get_series_empty_db(self):
        self.clean_db()
        result = self.query_engine.get_series()
        six.assertCountEqual(self, result, [])

    def test_get_series(self):
        metrics = [
            'test.series.one',
            'test.series.two'
        ]
        self.clean_db()
        self.create_test_data(metrics)

        result = self.query_engine.get_series()

        six.assertCountEqual(self, result, metrics)

    def test_build_influx_query(self):
        query = self.query_engine.build_influx_query('test.metric', 0, 500000)

        self.assertEqual(query, 'SELECT mean(value) AS value FROM test.metric WHERE time > 0s AND time <= 500000s GROUP BY time(300s)')

    def test_query(self):
        metrics = [
            'test.series.one',
            'test.series.two'
        ]
        self.clean_db()
        self.create_test_data(metrics)

        now = int(time.time())
        start = now - 5000
        end = now + 5000

        result = self.query_engine.query(metrics, start, end)

        self.assertEqual(result['from'], start)
        self.assertEqual(result['to'], end)
        self.assertEqual(result['step'], 600)
        six.assertCountEqual(self, result['series'], {
            'test.series.one': [1],
            'test.series.two': [1]
        })

    def test_lookup_aggregate(self):
        self.assertEqual(self.query_engine.lookup_aggregate('test.metric.sum'), 'sum')
        self.assertEqual(self.query_engine.lookup_aggregate('test.metric.gauge'), 'last')
        self.assertEqual(self.query_engine.lookup_aggregate('test.metric.randomness'), 'mean')

    def test_determine_interval(self):
        self.assertEqual(self.query_engine.determine_interval(0, 500), 60)
        self.assertEqual(self.query_engine.determine_interval(0, 5000), 300)
        self.assertEqual(self.query_engine.determine_interval(0, 50000), 600)

    def test_build_query_sets(self):
        sum_metrics = [
            'test.metric.one.sum',
            'test.metric.two.sum'
        ]

        mean_metrics = [
            'test.metric.whatever'
        ]

        last_metrics = [
            'test.metric.gauge'
        ]

        sets = self.query_engine.build_query_sets(sum_metrics + mean_metrics + last_metrics)

        six.assertCountEqual(self, sets, {
            'mean': mean_metrics,
            'last': last_metrics,
            'sum': sum_metrics
        })

if __name__ == '__main__':
    unittest.main()
