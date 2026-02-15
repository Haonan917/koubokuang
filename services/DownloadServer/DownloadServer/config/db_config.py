# -*- coding: utf-8 -*-
import os

# mysql (crawler data) config - single source of truth: CRAWLER_DB_*
CRAWLER_DB_HOST = os.getenv("CRAWLER_DB_HOST", os.getenv("RELATION_DB_HOST", "127.0.0.1"))
CRAWLER_DB_PORT = int(os.getenv("CRAWLER_DB_PORT", os.getenv("RELATION_DB_PORT", 3306)))
CRAWLER_DB_USER = os.getenv("CRAWLER_DB_USER", os.getenv("RELATION_DB_USER", "root"))
CRAWLER_DB_PASSWORD = os.getenv("CRAWLER_DB_PASSWORD", os.getenv("RELATION_DB_PWD", ""))
CRAWLER_DB_NAME = os.getenv("CRAWLER_DB_NAME", os.getenv("RELATION_DB_NAME", "media_crawler_pro"))

# Backward-compatible aliases (to be removed later)
RELATION_DB_HOST = CRAWLER_DB_HOST
RELATION_DB_PORT = CRAWLER_DB_PORT
RELATION_DB_USER = CRAWLER_DB_USER
RELATION_DB_PWD = CRAWLER_DB_PASSWORD
RELATION_DB_NAME = CRAWLER_DB_NAME

# crawler cache switch
CRAWLER_CACHE_ENABLED = os.getenv("CRAWLER_CACHE_ENABLED", "true").lower() == "true"
CRAWLER_CACHE_MAX_AGE_SECONDS = int(os.getenv("CRAWLER_CACHE_MAX_AGE_SECONDS", 86400))

# redis config
REDIS_DB_HOST = os.getenv("REDIS_DB_HOST", "127.0.0.1")
REDIS_DB_PWD = os.getenv("REDIS_DB_PWD", "")
REDIS_DB_PORT = int(os.getenv("REDIS_DB_PORT", 6379))
REDIS_DB_NUM = int(os.getenv("REDIS_DB_NUM", 0))

# cache type
CACHE_TYPE_REDIS = "redis"
CACHE_TYPE_MEMORY = "memory"
USE_CACHE_TYPE = os.getenv("USE_CACHE_TYPE", CACHE_TYPE_REDIS)
