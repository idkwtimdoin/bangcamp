import logging.config
import os
from logging import NOTSET, getLoggerClass, addLevelName, setLoggerClass


default_logging_config = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        "colored": {
            "class": "coloredlogs.ColoredFormatter",
            "format": "%(asctime)s %(filename)15s:%(lineno)-5s %(message)s",
            "datefmt": "%H:%M:%S.%02d"
        }
    },
    'handlers': {
        'default': {
            'class': 'logging.StreamHandler',
            'level': 'DEBUG',
            'formatter': 'colored',
            'stream': 'ext://sys.stdout'
        }
    },
    'loggers': {
        '': {
            'handlers': ['default'],
            'level': 'DEBUG',
            'propagate': False
        },
        '__main__': {
            'handlers': ['default'],
            'level': 'DEBUG',
            'propagate': False
        }
    }
}


class CustomLogger(getLoggerClass()):
    '''custom logger with additional logging levels'''
    SUCCESS = 35
    NOTICE = 25
    VERBOSE = 15
    SPAM = 12

    addLevelName(SUCCESS, 'SUCCESS')
    addLevelName(NOTICE, 'NOTICE')
    addLevelName(VERBOSE, 'VERBOSE')
    addLevelName(SPAM, 'SPAM')

    def __init__(self, name, level=NOTSET):
        super().__init__(name, level)

    def spam(self, msg, *args, **kwargs):
        if self.isEnabledFor(CustomLogger.SPAM):
            self._log(CustomLogger.SPAM, msg, args, **kwargs)

    def verbose(self, msg, *args, **kwargs):
        if self.isEnabledFor(CustomLogger.VERBOSE):
            self._log(CustomLogger.VERBOSE, msg, args, **kwargs)

    def notice(self, msg, *args, **kwargs):
        if self.isEnabledFor(CustomLogger.NOTICE):
            self._log(CustomLogger.NOTICE, msg, args, **kwargs)

    def success(self, msg, *args, **kwargs):
        if self.isEnabledFor(CustomLogger.SUCCESS):
            self._log(CustomLogger.SUCCESS, msg, args, **kwargs)


def config_logger(level: str):
    '''basic default logging config'''
    stream_handlers = [
        handler for handler in default_logging_config['handlers'].values()
        if handler['class'] == 'logging.StreamHandler'
    ]

    for handler in stream_handlers:
        handler['level'] = level.upper()

    logging.config.dictConfig(default_logging_config)


setLoggerClass(CustomLogger)
config_logger(os.getenv('logging_level', 'DEBUG'))
