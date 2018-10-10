Logsrash
========

Logsrash is a simple alternative to Logstash.

Written in Python 3.7+ it simply observes plain log files, parses
their lines and sends parsed result via configured output.

Logs are observed using threads.


Usage
-----

```python

import logsrash

logsrash.register('/path/to/local/logfile1', '<regexp>')
logsrash.register('/path/to/local/logfile2', '<regexp>')
logsrash.start()
logsrash.wait()  # blocking wait
```

To change the output just write (for example):

```python
logsrash.set_output(ElasticSearchOutput())
```

or aggregate all to one file:

```python
logsrash.set_output(logsrash.FileOutput('/tmp/aggregated.log'))
```

Stop collecting logs:

```python
logsrash.stop()
```


License
-------

GNU General Public License v3.0
