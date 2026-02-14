# -*- coding: utf-8 -*-
import logging
import traceback
from typing import Optional

from constant.error_code import ApiCode
from logic.creatory_query_logic import CreatorQueryLogic
from models.creator import (
    CreatorContentListRequest,
    CreatorContentListResponse,
    CreatorQueryRequest,
    CreatorQueryResponse,
)

from .base_handler import TornadoBaseReqHandler

logger = logging.getLogger(__name__)


class CreatorQueryHandler(TornadoBaseReqHandler):
    request_model = CreatorQueryRequest

    async def post(self):
        """
        查询创作者主页信息
        Returns:

        """
        req: Optional[CreatorQueryRequest] = self.parse_params()
        if not req:
            return

        logic = CreatorQueryLogic(platform=req.platform, cookies=req.cookies)
        await logic.async_initialize()

        try:
            is_valid = await logic.check_cookies()
            if not is_valid:
                self.return_error_info(
                    errorcode=ApiCode.INVALID_PARAMETER,
                    errmsg="无效的cookies，请检查cookies的登录态是否正确。",
                )
                return
            logger.info("[CreatorQueryHandler.post] Cookies is valid.")
        except Exception as e:
            logger.error(
                f"[CreatorQueryHandler.post] Check cookies failed: {traceback.format_exc()}"
            )
            self.return_error_info(
                errorcode=ApiCode.EXCEPTION, errmsg="检查cookies登录态失败。"
            )
            return

        extract_result, extract_msg, creator_user_id = logic.extract_creator_id(
            req.creator_url
        )
        if not extract_result:
            self.return_error_info(errorcode=ApiCode.EMPTY_RESULT, errmsg=extract_msg)
            return
        try:
            req.creator_id = creator_user_id
            response: Optional[CreatorQueryResponse] = await logic.query_creator_info(
                req
            )
            if not response:
                self.return_error_info(
                    errorcode=ApiCode.EMPTY_RESULT,
                    errmsg="创作者信息获取失败。",
                )
                return
            return self.return_ok(data=response)
        except Exception as e:
            logger.error(
                f"[CreatorQueryHandler.post] Query creator info failed: {traceback.format_exc()}"
            )
            self.return_error_info(errorcode=ApiCode.EXCEPTION, errmsg=str(e))


class CreatorContentListHandler(TornadoBaseReqHandler):
    request_model = CreatorContentListRequest

    async def post(self):
        """
        查询创作者内容
        """
        req: Optional[CreatorContentListRequest] = self.parse_params()
        if not req:
            return

        logic = CreatorQueryLogic(platform=req.platform, cookies=req.cookies)
        await logic.async_initialize()

        is_valid = await logic.check_cookies()
        if not is_valid:
            self.return_error_info(
                errorcode=ApiCode.INVALID_PARAMETER,
                errmsg="无效的cookies，请检查cookies的登录态是否正确。",
            )
            return

        try:
            response: CreatorContentListResponse = await logic.query_creator_contents(
                req
            )
            return self.return_ok(data=response)
        except Exception as e:
            logger.error(
                f"[CreatorContentListHandler.post] Query creator contents failed: {traceback.format_exc()}"
            )
            self.return_error_info(errorcode=ApiCode.EXCEPTION, errmsg=str(e))
