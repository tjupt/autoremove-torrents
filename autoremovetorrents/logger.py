# -*- coding:utf-8 -*-
# Logging System

import os
import logging
from datetime import datetime

class Logger(object):
    # Logger Settings
    LOG_FILE_NAME = 'autoremove.%s.log'
    DELETION_LOG_FILE_NAME = 'autoremove.deleted.%s.log'
    OUTPUT_FORMAT = '%(asctime)s %(name)s %(levelname)s: %(message)s'
    FILE_FORMAT = '%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s'
    DELETION_FORMAT = '%(asctime)s %(levelname)s %(message)s'
    DATE_FORMAT = '%a, %d %b %Y %H:%M:%S'

    # Log File Handler; Use FileHandler to output to file
    file_handler = None
    # Log Console Handler; Use StreamHandler to output to screen
    console_handler = None
    # Deletion Log File Handler; only records removal events
    deletion_handler = None
    # Logging path
    log_path = ''

    @staticmethod
    def init(log_path = '', file_debug_log = False, output_debug_log = False):
        # log_path：日志文件所在目录（不是具体 .log 文件路径）；最终文件名为 LOG_FILE_NAME + 当天日期
        Logger.log_path = log_path

        today = datetime.now().strftime('%Y-%m-%d')

        # Initialize the file handler
        Logger.file_handler = logging.FileHandler(
            os.path.join(Logger.log_path, Logger.LOG_FILE_NAME % today),
            encoding='utf-8'
        )
        Logger.file_handler.setLevel(logging.DEBUG if file_debug_log else logging.INFO)
        file_handler_formatter = logging.Formatter(Logger.FILE_FORMAT, datefmt=Logger.DATE_FORMAT)
        Logger.file_handler.setFormatter(file_handler_formatter)

        # Initialize the deletion log file handler
        Logger.deletion_handler = logging.FileHandler(
            os.path.join(Logger.log_path, Logger.DELETION_LOG_FILE_NAME % today),
            encoding='utf-8'
        )
        Logger.deletion_handler.setLevel(logging.INFO)
        deletion_formatter = logging.Formatter(Logger.DELETION_FORMAT, datefmt=Logger.DATE_FORMAT)
        Logger.deletion_handler.setFormatter(deletion_formatter)

        # Initialize the console handler
        Logger.console_handler = logging.StreamHandler()
        Logger.console_handler.setLevel(logging.DEBUG if output_debug_log else logging.INFO)
        console_handler_formatter = logging.Formatter(Logger.OUTPUT_FORMAT, datefmt=Logger.DATE_FORMAT)
        Logger.console_handler.setFormatter(console_handler_formatter)

    @staticmethod
    def register(name):
        logger = logging.getLogger(name)

        # Remove old loggers
        logger.handlers = []

        # Configure logging
        logger.setLevel(logging.DEBUG)

        # Add Handlers
        logger.addHandler(Logger.file_handler)
        logger.addHandler(Logger.console_handler)

        return logger

    @staticmethod
    def register_deletion_logger(name):
        """返回一个只写入删除日志文件的 logger，不输出到控制台。"""
        logger = logging.getLogger(name)
        logger.handlers = []
        logger.setLevel(logging.INFO)
        logger.propagate = False
        logger.addHandler(Logger.deletion_handler)
        return logger