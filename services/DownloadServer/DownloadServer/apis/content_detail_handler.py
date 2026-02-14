import logging
import traceback
from typing import Optional

from constant.error_code import ApiCode
from logic.content_detail_logic import ContentDetailLogic
from models.content_detail import ContentDetailRequest, ContentDetailResponse

from .base_handler import TornadoBaseReqHandler

logger = logging.getLogger(__name__)


class ContentDetailHandler(TornadoBaseReqHandler):
    request_model = ContentDetailRequest

    async def post(self):
        """
        查询内容详情
        """
        req: Optional[ContentDetailRequest] = self.parse_params()
        if not req:
            return

        logic = ContentDetailLogic(platform=req.platform, cookies=req.cookies)
        await logic.async_initialize()

        try:
            is_valid = await logic.check_cookies()
            if not is_valid:
                self.return_error_info(
                    errorcode=ApiCode.INVALID_PARAMETER,
                    errmsg="无效的cookies，请检查cookies的登录态是否正确。",
                )
                return
        except Exception as e:
            logger.error(
                f"[ContentDetailHandler.post] Check cookies failed: {traceback.format_exc()}"
            )
            self.return_error_info(
                errorcode=ApiCode.EXCEPTION, errmsg="检查cookies登录态失败。"
            )
            return
        try:
            is_valid, extract_msg, content_id = logic.extract_content_id(
                req.content_url
            )
            if not is_valid:
                self.return_error_info(
                    errorcode=ApiCode.INVALID_PARAMETER, errmsg=extract_msg
                )
                return

            response: Optional[ContentDetailResponse] = (
                await logic.query_content_detail(content_id, req.content_url)
            )
            if not response:
                self.return_error_info(
                    errorcode=ApiCode.EMPTY_RESULT, errmsg="内容详情获取失败。"
                )
                return
            return self.return_ok(data=response)
        except Exception as e:
            logger.error(
                f"[ContentDetailHandler.post] Query content detail failed: {traceback.format_exc()}"
            )
            self.return_error_info(errorcode=ApiCode.EXCEPTION, errmsg=str(e))
