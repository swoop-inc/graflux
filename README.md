# Graflux

An `influxdb` storage adapter for `graphite-api`.

## Design

Storing graphite metric data in influxdb provides a high performance read/write storage layer but poses an issue for metric name lookup. Graphite thinks of metrics as a directory structure where only leafs in the structure contain data, i.e. `apps.my_app.hits.count` is thought of like a file system `app/my_app/hits/count` where the data is stored only in `count`. Influx has no such model and just thinks of each metric name as a string, i.e. `apps.my_app.hits.count` is just a string and the `.` separators hold no meaning.

This creates a performance problem with looking up metrics in `influx`, a graphite query like `apps.my_app.*.count` has to be converted into a regex to query influx directly for matching series. Applying regexes across 300k+ series is a very slow operation. In addition intermediary queries for branches will return all children, e.g. a graphite query of `apps.*` is expected to only return immediate children of `apps`, but there is no way to query that with a regex in influx so it would return all metrics under `apps` and need to be post filtered. This is extremely slow for large numbers of metrics.

To work around these issues `graflux` constructs an in memory index of metric names rather than querying influx for them. The index is a k-ary directory tree like structure which can be queried with graphite's glob expression language. The index is periodically rebuilt and reloaded by each `graphite-api` process. The initial implementation uses file based storage and locking to ensure that only one process rebuilds the index and to share the resulting index with other processes. Additional storage implementations using memcached/redis are planned to support deployments with multiple boxes running `graphite-api`, PRs welcome and some provisions have been made in the code for this support.

The metric index gives `graflux` much higher performance than current alternatives. Metric lookup queries from a front end like `grafana` typically execute in less than 25ms total time with ~300k series. The index for 300k series is typically built in <10s and reloading occurs in <3s. The default settings refresh the index every 15m and load it every 5m meaning the index will be stale and not contain any newly created metrics for at most 20m. Both time settings are configurable and should be turned to be as low as possible without negatively impact overall performance.

## Status

We're using `graflux` in production with a fairly large setup, ~400k metrics in InfluxDB which are stored at 60s resolution. However `graflux` has not been tested against other workloads so YMMV. Please report any issues found.

## Compatibility

Under production load only python 2.7 + InfluxDB 0.9.x have been beat on.

Python 2.7, 3.5 and pypy are tested against InfluxDB 0.9.x and 0.10.2 in the test suite and are planned to be fully supported.

One thing that is interesting to explore is `pypy` I haven't tested it with `graphite-api` yet but in isolated benchmarks against the metric index build/load/query it is 5-10x faster than CPython.

## Installation

`pip install https://github.com/swoop-inc/graflux/archive/0.1.0.tar.gz`

## Configuration

`graflux` is configured via `graphite-api.yml`. An example configuration with commentary is available in `config/graphite-api.yml`.

#### Pre-aggregate calculation

Since Influx is efficient at storing high resolution data for long periods of time we generally don't pre-compute roll ups, but this can create issues when querying long time periods. For example if you collect data every 10s you don't want to have to load 86400 * 31 samples to graph data for 1 month. `graflux` can have `Influxdb` do an initial rollup before sending the data to avoid massive IO and `graphite-api` process time.

To configure this use the `steps` and `aggregates` configuration, this is fairly similar to setting up retention and aggregates in `carbon`.

An example:

config:

```yaml
  steps:
    - [86400, 10]
    - [259200, 60]
    - [604800, 300]
    - [1209600, 600]
  aggregates:
    - [\.count$, sum]
    - [\.gauge$, last]
```

A request from graphite-api for up to 1 day (86400s) of data for a metric will use a 10s group time, determined by comparing the time span of the query against the lookup table in `steps`. A query for between 1 and 3 days (259200s) of data would instead use 60s as the group time, etc.

The aggregate function used is determined by matching the regexes defined in `aggregates` against the metric name, first match wins. So `test.metric.count` will use `sum`, `test.metric.gauge$` will use `last`, if no match is found then `mean` is used by default.

NOTE: for protection against killing `graphite-api` and `grafana`, `graflux` always uses an aggregate query with a group clause so it is important to at least configure `aggregates` to match your metric naming conventions. Additionally `InfluxDB` has a 10,000 data point limit on queries so I recommend using the example `steps` config or tweaking it to your liking, currently no provision is made for loading more than 10,000 data points per series from `InfluxDB`, you'll simply see truncated data.

## License

MIT


