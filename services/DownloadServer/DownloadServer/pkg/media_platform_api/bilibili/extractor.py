from ast import main
import json
import re
import logging
from typing import Dict, List, Optional
import urllib.parse

from constant.bilibili import BILI_INDEX_URL
from models.base_model import ContentTypeEnum
from models.content_detail import (
    AuthorInfo,
    Content,
    ContentDetailResponse,
    InteractionInfo,
)
from models.creator import CreatorContentListResponse, CreatorQueryResponse

logger = logging.getLogger(__name__)


class BiliExtractor:

    def extract_creator_info(
        self, up_info: Dict, relation_state: Dict, space_navnum: Dict
    ) -> Optional[CreatorQueryResponse]:
        """
        提取B站主页信息

        Args:
            up_info (Dict): B站用户信息
            relation_state (Dict): B站用户关系状态
            space_navnum (Dict): B站用户空间导航栏数据

        Returns:
            CreatorQueryResponse: 创作者信息
        """
        logger.debug(up_info, relation_state, space_navnum)
        if not up_info or not relation_state or not space_navnum:
            return None

        res_creator = CreatorQueryResponse(
            nickname=up_info.get("name", ""),
            avatar=up_info.get("face", ""),
            description=up_info.get("sign", ""),
            user_id=str(up_info.get("mid", "")),
            follower_count=str(relation_state.get("follower", "0")),
            following_count=str(relation_state.get("following", "0")),
            content_count=str(space_navnum.get("video", "0")),
        )
        return res_creator

    def extract_w_webid(self, html: str) -> str:
        """
        提取w_webid

        Args:
            html (str): B站主页HTML

        Returns:
            str: w_webid
        """
        __RENDER_DATA__ = re.search(
            r"<script id=\"__RENDER_DATA__\" type=\"application/json\">(.*?)</script>",
            html,
            re.S,
        ).group(1)
        w_webid = json.loads(urllib.parse.unquote(__RENDER_DATA__))["access_id"]
        return w_webid

    def extract_author_info_from_video_detail(self, video_info: Dict) -> AuthorInfo:
        """
        从视频详情中提取作者信息

        Args:
            video_info (Dict): B站视频详情

        Returns:
            AuthorInfo: 作者信息
        """
        owner = video_info.get("owner", {})
        mid = owner.get("mid", "")
        return AuthorInfo(
            user_id=str(mid),
            nickname=owner.get("name", ""),
            avatar=owner.get("face", ""),
            profile_url=f"https://space.bilibili.com/{mid}" if mid else "",
        )

    def extract_interaction_info_from_video_detail(
        self, video_info: Dict
    ) -> InteractionInfo:
        """
        从视频详情中提取互动数据

        Args:
            video_info (Dict): B站视频详情

        Returns:
            InteractionInfo: 互动数据
        """
        stat = video_info.get("stat", {})
        return InteractionInfo(
            liked_count=str(stat.get("like", "")),
            collected_count=str(stat.get("favorite", "")),
            comment_count=str(stat.get("reply", "")),
            share_count=str(stat.get("share", "")),
            play_count=str(stat.get("view", "")),
            danmaku_count=str(stat.get("danmaku", "")),
        )

    def extract_creator_contents(
        self, current_cursor: int, videos_res: Dict
    ) -> List[Content]:
        """
        提取创作者内容

        Args:
            current_cursor (int): 当前页码
            videos_res (Dict): B站创作者内容列表

        Returns:
            CreatorContentListResponse: 创作者内容列表
        """
        video_list = videos_res.get("list", {}).get("vlist", [])
        next_cursor = str(videos_res.get("page").get("pn") + 1)
        has_more = videos_res.get("page").get("count") > current_cursor * 30
        contents: List[Content] = []
        for video in video_list:
            # 提取作者信息 (列表接口数据有限)
            mid = video.get("mid", "")
            author = AuthorInfo(
                user_id=str(mid),
                nickname=video.get("author", ""),
                avatar="",  # 列表接口无头像
                profile_url=f"https://space.bilibili.com/{mid}" if mid else "",
            )

            # 提取互动数据 (列表接口数据有限，完整数据需查询视频详情)
            interaction = InteractionInfo(
                comment_count=str(video.get("comment", "")),
                play_count=str(video.get("play", "")),
                danmaku_count=str(video.get("video_review", "")),  # 弹幕数
            )

            contents.append(
                Content(
                    id=str(video.get("bvid", "")),
                    url=f"{BILI_INDEX_URL}/video/{video.get('bvid', '')}",
                    title=video.get("title", ""),
                    desc=video.get("description", ""),
                    content_type=ContentTypeEnum.VIDEO,
                    cover_url=video.get("pic", ""),
                    image_urls=[],
                    video_download_url="",
                    author=author,
                    interaction=interaction,
                )
            )
        return CreatorContentListResponse(
            contents=contents, has_more=has_more, next_cursor=next_cursor
        )
