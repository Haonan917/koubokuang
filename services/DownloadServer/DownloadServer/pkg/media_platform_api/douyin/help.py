# -*- coding: utf-8 -*-
import asyncio
import random
import time

import httpx
from httpx import RequestError
from pydantic import BaseModel, Field

from constant.douyin import (DOUYIN_FIXED_USER_AGENT,
                             DOUYIN_MS_TOKEN_REQ_STR_DATA,
                             DOUYIN_MS_TOKEN_REQ_URL, DOUYIN_WEBID_REQ_URL)
from pkg.async_http_client import AsyncHTTPClient
from pkg.tools import utils


class DataFetchError(RequestError):
    """something error when fetch"""


class IPBlockError(RequestError):
    """fetch so fast that the server block us ip"""


class CommonVerfiyParams(BaseModel):
    ms_token: str = Field(..., title="ms_token", description="ms_token")
    webid: str = Field(..., title="webid", description="webid")
    verify_fp: str = Field(..., title="verify_fp", description="verify_fp")
    s_v_web_id: str = Field(..., title="s_v_web_id", description="s_v_web_id")


async def get_common_verify_params(user_agent: str) -> CommonVerfiyParams:
    """
    获取通用验证参数
    Args:
        user_agent:

    Returns:

    """
    token_manager = TokenManager(user_agent)
    ms_token = await token_manager.get_msToken()
    webid = await token_manager.gen_webid()
    verify_fp = VerifyFpManager.gen_verify_fp()
    s_v_web_id = VerifyFpManager.gen_s_v_web_id()
    return CommonVerfiyParams(
        ms_token=ms_token, webid=webid, verify_fp=verify_fp, s_v_web_id=s_v_web_id
    )


def get_web_id():
    """
    生成随机的webid
    Returns:

    """

    def e(t):
        if t is not None:
            return str(t ^ (int(16 * random.random()) >> (t // 4)))
        else:
            return "".join(
                [
                    str(int(1e7)),
                    "-",
                    str(int(1e3)),
                    "-",
                    str(int(4e3)),
                    "-",
                    str(int(8e3)),
                    "-",
                    str(int(1e11)),
                ]
            )

    web_id = "".join(e(int(x)) if x in "018" else x for x in e(None))
    return web_id.replace("-", "")[:19]


class TokenManager:
    """
    # copy from https://github.com/johnserf-seed/f2 thanks for johnserf-seed
    # modified by relakkes@gmail.com
    """

    def __init__(self, user_agent: str):
        self._user_agent = user_agent

    async def gen_real_msToken(self) -> str:
        """
        生成真实的 msToken。
        Returns:

        """
        async with AsyncHTTPClient() as client:
            post_data = {
                "magic": 538969122,
                "version": 1,
                "dataType": 8,
                "strData": DOUYIN_MS_TOKEN_REQ_STR_DATA,
                "tspFromClient": utils.get_current_timestamp(),
                "url": 0,
            }
            headers = {
                "Content-Type": "application/json; charset=utf-8",
                "User-Agent": self._user_agent,
            }
            response = await client.post(
                DOUYIN_MS_TOKEN_REQ_URL, json=post_data, headers=headers
            )
            ms_token = str(httpx.Cookies(response.cookies).get("msToken"))
            if len(ms_token) not in [120, 128]:
                raise Exception(f"获取msToken内容不符合要求: {ms_token}")
            return ms_token

    @classmethod
    def gen_fake_msToken(cls) -> str:
        """
        生成假的msToken
        Returns:

        """
        false_ms_token = utils.get_random_str(126) + "=="
        return false_ms_token

    async def get_msToken(self) -> str:
        """
        获取 msToken
        Returns:

        """
        try:
            return await self.gen_real_msToken()
        except Exception as e:
            utils.logger.warning(f"gen_real_msToken error: {e}, return a fake msToken")
            return self.gen_fake_msToken()

    async def gen_webid(self) -> str:
        """
        生成个性化追踪webid (Generate personalized tracking webid)

        Returns:
            str: 生成的webid (Generated webid)
        """
        async with AsyncHTTPClient() as client:
            post_data = {
                "app_id": 6383,
                "referer": f"https://www.douyin.com/",
                "url": "https://www.douyin.com/",
                "user_agent": self._user_agent,
                "user_unique_id": "",
            }
            headers = {
                "User-Agent": self._user_agent,
                "Content-Type": "application/json; charset=UTF-8",
                "Referer": "https://www.douyin.com/",
            }
            try:
                response = await client.post(
                    DOUYIN_WEBID_REQ_URL, json=post_data, headers=headers
                )
                webid = response.json().get("web_id")
                if not webid:
                    raise Exception("获取webid失败")
                return webid
            except Exception as e:
                utils.logger.warning(f"gen_webid error: {e}, return a random webid")
                return get_web_id()


class VerifyFpManager:
    """
    copy from https://github.com/johnserf-seed/f2 thanks for johnserf-seed
    """

    @classmethod
    def gen_verify_fp(cls) -> str:
        """
        生成verifyFp 与 s_v_web_id (Generate verifyFp)
        """
        base_str = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
        t = len(base_str)
        milliseconds = int(round(time.time() * 1000))
        base36 = ""
        while milliseconds > 0:
            remainder = milliseconds % 36
            if remainder < 10:
                base36 = str(remainder) + base36
            else:
                base36 = chr(ord("a") + remainder - 10) + base36
            milliseconds = int(milliseconds / 36)
        r = base36
        o = [""] * 36
        o[8] = o[13] = o[18] = o[23] = "_"
        o[14] = "4"

        for i in range(36):
            if not o[i]:
                n = 0 or int(random.random() * t)
                if i == 19:
                    n = 3 & n | 8
                o[i] = base_str[n]

        return "verify_" + r + "_" + "".join(o)

    @classmethod
    def gen_s_v_web_id(cls) -> str:
        return cls.gen_verify_fp()


async def test_token_manager():
    user_agent = DOUYIN_FIXED_USER_AGENT
    token_manager = TokenManager(user_agent)
    ms_token = await token_manager.get_msToken()
    webid = await token_manager.gen_webid()
    verify_fp = VerifyFpManager.gen_verify_fp()
    s_v_web_id = VerifyFpManager.gen_s_v_web_id()
    utils.logger.info(
        f"ms_token: {ms_token}, webid: {webid}, verify_fp: {verify_fp}, s_v_web_id: {s_v_web_id}"
    )


if __name__ == "__main__":
    asyncio.run(test_token_manager())
