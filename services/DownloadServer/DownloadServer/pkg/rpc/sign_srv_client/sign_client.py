# -*- coding: utf-8 -*-
import asyncio
from typing import Any, Dict, Union

import httpx

import config
from pkg.rpc.sign_srv_client.sign_model import (BilibliSignRequest,
                                                BilibliSignResponse,
                                                DouyinSignRequest,
                                                DouyinSignResponse,
                                                XhsSignRequest,
                                                XhsSignResponse)
from pkg.tools import utils

SIGN_SERVER_URL = f"http://{config.SIGN_SRV_HOST}:{config.SIGN_SRV_PORT}"


class SignServerClient:
    def __init__(self, endpoint: str = SIGN_SERVER_URL, timeout: int = 60):
        """
        SignServerClient constructor
        Args:
            endpoint: sign server endpoint
            timeout: request timeout
        """
        self._endpoint = endpoint
        self._timeout = timeout

    async def request(self, method: str, uri: str, **kwargs) -> Union[Dict, Any]:
        """
        send request
        Args:
            method: request method
            uri: request uri
            **kwargs: other request params

        Returns:

        """
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Connection": "close",
        }
        try:
            # 20250104 @relakkes@gmail.com httpx如果在本机电脑中开启科学上网（如：clashx、shadowrocket），这个时候往签名服务器请求会报错502，之前遇到过没解决，当时也排除了很久，今天又肝好久了，今天终于找到原因了！
            # httpx底层默认会自动读取和使用系统环境变量中的代理设置（HTTP_PROXY、HTTPS_PROXY 等），所以加上一个参数：trust_env=False，禁止使用系统环境变量中的代理设置，即使开启VPN代理也没事了
            async with httpx.AsyncClient(timeout=self._timeout,  http2=False, headers=headers, trust_env=False) as client:
                response = await client.request(method, self._endpoint + uri, **kwargs)
                if response.status_code != 200:
                    utils.logger.error(
                        f"[SignServerClient.request] response status code {response.status_code} response content: {response.text}"
                    )
                    raise Exception(
                        f"请求签名服务器失败，状态码：{response.status_code}, response content: {response.text}"
                    )

                return response.json()
        except Exception as e:
            raise Exception(f"请求签名服务器失败, error: {e}")

    async def xiaohongshu_sign(self, sign_req: XhsSignRequest) -> XhsSignResponse:
        """
        xiaohongshu sign request to sign server
        Args:
            sign_req:

        Returns:

        """
        sign_server_uri = "/signsrv/v1/xhs/sign"
        res_json = await self.request(
            method="POST", uri=sign_server_uri, json=sign_req.model_dump()
        )
        if not res_json:
            raise Exception(
                f"从签名服务器:{SIGN_SERVER_URL}{sign_server_uri} 获取签名失败"
            )

        xhs_sign_response = XhsSignResponse(**res_json)
        if xhs_sign_response.isok:
            return xhs_sign_response
        raise Exception(
            f"从签名服务器:{SIGN_SERVER_URL}{sign_server_uri} 获取签名失败，原因：{xhs_sign_response.msg}, sign reponse: {xhs_sign_response}"
        )

    async def douyin_sign(self, sign_req: DouyinSignRequest) -> DouyinSignResponse:
        """
        douyin sign request to sign server
        Args:
            sign_req: DouyinSignRequest object

        Returns:

        """
        sign_server_uri = "/signsrv/v1/douyin/sign"
        res_json = await self.request(
            method="POST", uri=sign_server_uri, json=sign_req.model_dump()
        )
        if not res_json:
            raise Exception(
                f"从签名服务器:{SIGN_SERVER_URL}{sign_server_uri} 获取签名失败"
            )

        sign_response = DouyinSignResponse(**res_json)
        if sign_response.isok:
            return sign_response
        raise Exception(
            f"从签名服务器:{SIGN_SERVER_URL}{sign_server_uri} 获取签名失败，原因：{sign_response.msg}, sign reponse: {sign_response}"
        )

    async def bilibili_sign(self, sign_req: BilibliSignRequest) -> BilibliSignResponse:
        """
        bilibili sign request to sign server
        Args:
            sign_req:

        Returns:

        """
        sign_server_uri = "/signsrv/v1/bilibili/sign"
        res_json = await self.request(
            method="POST", uri=sign_server_uri, json=sign_req.model_dump()
        )
        if not res_json:
            raise Exception(
                f"从签名服务器:{SIGN_SERVER_URL}{sign_server_uri} 获取签名失败"
            )
        sign_response = BilibliSignResponse(**res_json)
        if sign_response.isok:
            return sign_response
        raise Exception(
            f"从签名服务器:{SIGN_SERVER_URL}{sign_server_uri} 获取签名失败，原因：{sign_response.msg}, sign reponse: {sign_response}"
        )

    async def pong_sign_server(self):
        """
        test
        :return:
        """
        utils.logger.info(
            "[SignServerClient.pong_sign_server] test xhs sign server is alive"
        )
        await self.request(method="GET", uri="/signsrv/pong")
        utils.logger.info(
            "[SignServerClient.pong_sign_server] xhs sign server is alive"
        )


if __name__ == "__main__":
    sign_client = SignServerClient()
    asyncio.run(sign_client.pong_sign_server())
