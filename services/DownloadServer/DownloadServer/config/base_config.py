# -*- coding: utf-8 -*-
import os

ENABLE_LOG_FILE = True
IS_DEBUG = bool(os.getenv("IS_DEBUG", True))
LOGGER_LEVEL = os.getenv("LOGGER_LEVEL", "INFO")

# app config
APP_HOST = os.getenv("APP_HOST", "127.0.0.1")
APP_PORT = int(os.getenv("APP_PORT", 8205))

# sign server config
SIGN_SRV_HOST = os.getenv('SIGN_SRV_HOST', '127.0.0.1')
SIGN_SRV_PORT = os.getenv('SIGN_SRV_PORT', '8989')