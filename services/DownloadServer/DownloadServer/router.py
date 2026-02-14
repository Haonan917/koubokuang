# -*- coding: utf-8 -*-
from apis.base_handler import PongHandler
from apis.content_detail_handler import ContentDetailHandler
from apis.creator_query_handler import (CreatorContentListHandler,
                                        CreatorQueryHandler)

all_router = [
    (r"/", PongHandler),
    (r"/ping", PongHandler),
    (r"/api/v1/creator_query", CreatorQueryHandler),
    (r"/api/v1/creator_contents", CreatorContentListHandler),
    (r"/api/v1/content_detail", ContentDetailHandler),
]
