import six
import unittest

import time

from graflux.metric_lookup import MetricLookup

from influxdb import InfluxDBClient
import influxdb.exceptions


class QueryEngineTest(unittest.TestCase):
    def setUp(self):
        self.db = 'graflux_test'
        self.config = {
            'influxdb': {
                'host': 'localhost',
                'port': 8086,
                'user': 'root',
                'password': 'root',
                'db': self.db
            },
            'index': {
                'build_interval': 10,
                'load_interval': 5,
                'storage': 'file',
                'path': '/tmp'
            }
        }

        self.client = InfluxDBClient(database=self.db)
        self.metric_lookup = MetricLookup(self.config)
        self.metric_lookup.delete_index()
        self.metric_lookup.storage.release_update_lock()
        self.clean_db()

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
                } for metric in metrics]

        self.assertTrue(self.client.write_points(data))

    def test_background_update(self):
        metrics = [
            'test.series.one',
            'test.series.two'
        ]

        self.create_test_data(metrics)

        self.metric_lookup.start_background_refresh()

        time.sleep(10)  # allow background threads time to process

        six.assertCountEqual(self, self.metric_lookup.query('test.series.*'), [
            {'is_leaf': True, 'metric': metric} for metric in metrics
        ])

        self.metric_lookup.stop_background_refresh()

if __name__ == '__main__':
    unittest.main()
