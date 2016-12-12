```
'elastic_log': {
                'class': 'elastic_logger.handler.LogHandler',
                'level': 'DEBUG',
                'formatter': 'json',
                'url': 'http://example.com:9200',
                'logs_drain_count': 10,
                'logs_drain_timeout': 50,
                'index': 'indx_name',
                'index_type': 'type',
                'log_type': "log_type_name"
            }
```

*Config Options*
- index - Index name
- type - Index Type
- logs_drain_count - Number of logs to keep in buffer before draining
- logs_drain_timeout - Time to wait before draining, regardless of the previouse setting
- log_type - Log type, for searching (defaults to "python")
- url - Url to elastic search