# Monitoring with statsd and Graphite

If you would like to monitor some part of code, this is the best tool you could use.
You can pass and aggregate different data types. The data types statsd supports are counters, timers, and gauges. For more info see [here](https://statsd.readthedocs.io/en/latest/types.html).

We use a hosted service for graphite and statsd that is added as a Heroku add-on to the `zc-statsd` app on Heroku.

## Installation

To install statsd in the project add the following lines to your `settings.py` file:

```python
STATSD_ENABLED = strtobool(os.environ.get('STATSD_ENABLED', 'False'))

if STATSD_ENABLED:
    STATSD_API_KEY = os.environ.get('STATSD_API_KEY')
    STATSD_HOST = os.environ.get('STATSD_HOST')
    STATSD_PORT = os.environ.get('STATSD_PORT', 8125)
    STATSD_PREFIX = '.'.join([STATSD_API_KEY, SERVICE_NAME])
```

Add the following to your `requirements.py` file:

```
statsd==3.2.1 # or higher
zc-common==0.3.12 # or higher
```

Also add the following environment variables to the heroku app:

- `STATSD_ENABLED`
- `STATSD_HOST`
- `STATSD_PORT`
- `STATSD_API_KEY`

## Usage

To send data to the statsd server include the following code in your module:

```
from zc_common.monitoring import statsd
```

In the above line, `statsd` is a statsd client and you can follow the instructions from the [statsd python module](https://statsd.readthedocs.io/en/latest/index.html).

Timers are special kind of data types that can be used in different ways, for more details check out the [docs](https://statsd.readthedocs.io/en/latest/timing.html).
