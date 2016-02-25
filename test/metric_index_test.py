import six
import unittest

from graflux.metric_index import MetricIndex


class MetricIndexTest(unittest.TestCase):

    def test_query(self):
        metrics = [
            'one.two.three.count',
            'one.two.three.gauge',
            'one.two.four.count',
            'two.two.three.count'
        ]

        index = MetricIndex()

        for metric in metrics:
            index.insert(metric)

        six.assertCountEqual(self, index.query('*'), [
            {'metric': 'one', 'is_leaf': False},
            {'metric': 'two', 'is_leaf': False},
        ])

        six.assertCountEqual(self, index.query('*.*'), [
            {'metric': 'one.two', 'is_leaf': False},
            {'metric': 'two.two', 'is_leaf': False},
        ])

        six.assertCountEqual(self, index.query('o*'), [
            {'metric': 'one', 'is_leaf': False}
        ])

        six.assertCountEqual(self, index.query('{one,two}.two.three.*'), [
            {'metric': 'one.two.three.count', 'is_leaf': True},
            {'metric': 'one.two.three.gauge', 'is_leaf': True},
            {'metric': 'two.two.three.count', 'is_leaf': True}
        ])

        six.assertCountEqual(self, index.query('*.*.*.*.*.*.*'), [])

    def test_to_from_json(self):
        metrics = [
            'one.two.three.count',
            'two.two.three.count'
        ]

        index = MetricIndex()

        for metric in metrics:
            index.insert(metric)

        six.assertCountEqual(self, index.query('*.*.*.*'), [
            {'metric': 'one.two.three.count', 'is_leaf': True},
            {'metric': 'two.two.three.count', 'is_leaf': True}
        ])

if __name__ == '__main__':
    unittest.main()
