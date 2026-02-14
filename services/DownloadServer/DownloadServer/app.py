# -*- coding: utf-8 -*-
import asyncio
import logging
import os
import sys

import tornado.web
from tornado.options import define, options

import config
import router
from context_vars import request_id_var

logger = logging.getLogger(__name__)


def register_all_handlers(all_handlers):
    """
    注册路由
    :param all_handlers:
    :return:
    """
    all_handlers += router.all_router


class LoggerCustomFilter(logging.Filter):
    def filter(self, record):
        record.request_id = request_id_var.get("-")
        return True


class Application(tornado.web.Application):
    all_handlers = []

    def __init__(self):
        register_all_handlers(Application.all_handlers)
        settings = dict(
            debug=config.IS_DEBUG,
            gzip=True,
            autoreload=True,
        )
        super(Application, self).__init__(Application.all_handlers, **settings)


async def init():
    """
    程序启动前的初始化代码
    :return:
    """

    # 初始化logger，logger中包含了request id
    logging.basicConfig(
        datefmt='%Y-%m-%d %H:%M:%S',
        level=config.LOGGER_LEVEL,
        format="%(asctime)s %(levelname)s %(filename)s:%(lineno)d req_id: %(request_id)s %(message)s",
    )
    log_filter = LoggerCustomFilter()
    for handler in logging.getLogger().handlers:
        handler.addFilter(log_filter)

    # 将项目根目录添加到sys.path
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    sys.path.insert(0, project_root)


define(name="port", default=config.APP_PORT, type=int, help="app http listen port")
define(name="host", default=config.APP_HOST, type=str, help="app http listen host")


async def create_app():
    await init()
    app = Application()
    app.listen(port=options.port, address=options.host)
    logger.info("MediaCrawlerDownloadBackend running at port %s", options.port)
    if config.IS_DEBUG:
        logger.info("MediaCrawlerDownloadBackend running in debug mode, debug url: http://localhost:%s", options.port)
    await asyncio.Event().wait()


if __name__ == '__main__':
    asyncio.run(create_app())
