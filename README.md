# Graflux

An `influxdb` storage adapter for `graphite-api`.

## Design

Storing graphite metric data in influxdb provides a high performance read/write storage layer but poses an issue for metric name lookup. Graphite thinks of metrics as a directory structure where only leafs in the structure contain data, i.e. `apps.my_app.hits.count` is thought of like a file system `app/my_app/hits/count` where the data is stored only in `count`. Influx has no such model and just thinks of each metric name as a string, i.e. `apps.my_app.hits.count` is just a string and the `.` separators hold no meaning.

This creates a performance problem with looking up metrics in `influx`, a graphite query like `apps.my_app.*.count` has to be converted into a regex to query influx directly for matching series. Applying regexes across 100k+ series is a very slow operation. In addition intermediary queries for branches will return all children, e.g. a graphite query of `apps.*` is expected to only return immediate children of `apps`, but there is no way to query that with a regex in influx so it would return all metrics under `apps` and need to be post filtered. This is extremely slow for large numbers of metrics.

To work around these issues `graflux` constructs an in memory index of metric names rather than querying influx for them. The index is a k-ary directory tree like structure which can be queried with graphite's glob expression language. The index is periodically rebuilt and reloaded by each `graphite-api` process. The initially implementation uses file based storage and locking to ensure that only one process rebuilds the index and to share the resulting index with other processes. Additional storage implementations using memcached/redis are planned to support deployments with multiple boxes running `graphite-api`.

This index gives `graflux` much better performance than current alternatives. Metric lookup queries from a front end like `grafana` typically execute in less than 50ms total time with ~300k series. The index for 300k series is typically built in <10s and reloading occurs in <3s. The default settings refresh the index every 15m and load it every 5m meaning the index will be stale and not contain any newly created for at most 20m. Both settings are configurable and should be turned to be as low as possible without negatively impact overall performance.

## Usage

TODO

