import json
import re
from typing import Dict, List, Optional

import humps

from constant.xiaohongshu import (
    XHS_INDEX_URL,
    XHS_NOTE_TYPE,
    XHS_VIDEO_CDN_URL,
    XHS_VIDEO_TYPE,
)
from models.base_model import ContentTypeEnum
from models.content_detail import (
    AuthorInfo,
    Content,
    ContentDetailResponse,
    InteractionInfo,
)
from models.creator import CreatorContentListResponse, CreatorQueryResponse


class XhsExtractor:

    def extract_creator_info(self, response: Dict) -> Optional[CreatorQueryResponse]:
        """
        提取小红书主页信息

        Args:
            response (Dict): 小红书用户信息

        Returns:
            CreatorQueryResponse: 创作者信息
        """
        user = response.get("user", {})
        if not user:
            return None

        user_page_data = user.get("userPageData", {})
        user_info = user_page_data.get("basicInfo", {})
        follows = 0
        fans = 0
        interaction = 0
        for i in user_page_data.get("interactions"):
            if i.get("type") == "follows":
                follows = i.get("count")
            elif i.get("type") == "fans":
                fans = i.get("count")
            elif i.get("type") == "interaction":
                interaction = i.get("count")

        return CreatorQueryResponse(
            nickname=user_info.get("nickname"),
            user_id="",
            avatar=user_info.get("images"),
            description=user_info.get("desc"),
            follower_count=str(fans),
            following_count=str(follows),
            content_count="未知",
        )

    def _extract_video_download_url(self, note_item: Dict) -> str:
        """
        提取视频下载地址

        Args:
            note_item (Dict): 小红书内容

        Returns:
            str: 视频下载地址
        """
        video_info = note_item.get("video")
        if not video_info:
            return ""

        video_stream = video_info.get("media", {}).get("stream", {}).get("h264", [])
        if not video_stream:
            return ""
        return video_stream[0]["master_url"]

    def _extract_note_cover_url(self, note_item: Dict) -> str:
        """
        提取小红书内容封面地址

        Args:
            note_item (Dict): 小红书内容

        Returns:
            str: 小红书内容封面地址
        """
        return note_item.get("cover", {}).get("url_default", "")

    def _extract_note_image_urls(self, note_item: Dict) -> List[str]:
        """
        提取小红书内容图片地址

        Args:
            note_item (Dict): 小红书内容

        Returns:
            List[str]: 小红书内容图片地址
        """
        res_image_urls = []
        image_list = note_item.get("image_list", [])
        for image_item in image_list:
            image_url = image_item.get("url_default", "")
            if image_url:
                res_image_urls.append(image_url)
        return res_image_urls

    def _extract_note_title(self, note_item: Dict) -> str:
        """
        提取小红书内容标题

        Args:
            note_item (Dict): 小红书内容

        Returns:
            str: 小红书内容标题
        """
        return note_item.get("display_title", "") or note_item.get("title", "")

    def _extract_note_detail_url(self, note_item: Dict) -> str:
        """
        提取小红书内容详情地址

        Args:
            note_item (Dict): 小红书内容

        Returns:
            str: 小红书内容详情地址
        """
        return f"{XHS_INDEX_URL}/explore/{note_item.get('note_id')}?xsec_token={note_item.get('xsec_token')}&xsec_source=pc_user"

    def _extract_author_info(self, note_item: Dict) -> AuthorInfo:
        """
        提取作者信息

        Args:
            note_item (Dict): 小红书内容

        Returns:
            AuthorInfo: 作者信息
        """
        user_data = note_item.get("user", {})
        user_id = user_data.get("user_id", "")
        return AuthorInfo(
            user_id=user_id,
            nickname=user_data.get("nickname", ""),
            avatar=user_data.get("avatar", ""),
            profile_url=f"https://www.xiaohongshu.com/user/profile/{user_id}"
            if user_id
            else "",
        )

    def _extract_interaction_info(self, note_item: Dict) -> InteractionInfo:
        """
        提取互动数据

        Args:
            note_item (Dict): 小红书内容

        Returns:
            InteractionInfo: 互动数据
        """
        interact_info = note_item.get("interact_info", {})
        return InteractionInfo(
            liked_count=str(interact_info.get("liked_count", "")),
            collected_count=str(interact_info.get("collected_count", "")),
            comment_count=str(interact_info.get("comment_count", "")),
            share_count=str(interact_info.get("share_count", "")),
        )

    def _extract_content_detail_from_user_profile(self, note_item: Dict) -> Content:
        """
        提取小红书内容详情
        Args:
            note_item (Dict): 小红书内容

        Returns:
            Content: 小红书内容详情
        """
        if note_item.get("type") == XHS_NOTE_TYPE:
            content_type = ContentTypeEnum.NOTE
        elif note_item.get("type") == XHS_VIDEO_TYPE:
            content_type = ContentTypeEnum.VIDEO
        else:
            return None

        content = Content(
            id=note_item.get("note_id"),
            title=self._extract_note_title(note_item),
            desc=note_item.get("desc", ""),
            url=self._extract_note_detail_url(note_item),
            content_type=content_type,
            cover_url=self._extract_note_cover_url(note_item),
            image_urls=self._extract_note_image_urls(note_item),
            video_download_url=self._extract_video_download_url(note_item),
            author=self._extract_author_info(note_item),
            interaction=self._extract_interaction_info(note_item),
        )
        if not content.cover_url and len(content.image_urls) > 0:
            content.cover_url = content.image_urls[0]
        return content

    def extract_contents_from_user_profile(
        self, response: Dict
    ) -> CreatorContentListResponse:
        """
        提取小红书内容
        # 小红书用户主页地址接口没有返回图片列表，所以这里返回空列表
        # 视频地址也是没有的，所以对于客户端来说，查询用户主页数据时，先不要去拉取帖子详情（这个接口容易风控）
        # 只有当选中要下载的帖子时，再去拉取帖子详情
        Args:
            response (Dict): 小红书内容

        Returns:
            CreatorContentListResponse: 创作者内容列表响应
        """
        res_contents: List[Content] = []
        note_list = response.get("notes", [])
        has_more = response.get("has_more", False)
        next_cursor = response.get("cursor", "")
        for note_item in note_list:
            content = self._extract_content_detail_from_user_profile(note_item)
            if content:
                res_contents.append(content)
        return CreatorContentListResponse(
            contents=res_contents,
            has_more=has_more,
            next_cursor=str(next_cursor),
        )

    def extract_content_detail(
        self, note_card: Dict
    ) -> Optional[ContentDetailResponse]:
        """
        提取小红书内容详情

        Args:
            note_card (Dict): 小红书内容详情

        Returns:
            ContentDetailResponse: 小红书内容详情
        """

        base_extract_content = self._extract_content_detail_from_user_profile(note_card)
        if not base_extract_content:
            return None
        return ContentDetailResponse(content=base_extract_content)

    def extract_note_detail_from_html(self, note_id: str, html: str) -> Optional[Dict]:
        """从html中提取笔记详情

        Args:
            html (str): html字符串

        Returns:
            Dict: 笔记详情字典
        """
        if "noteDetailMap" not in html:
            # 这种情况要么是出了验证码了，要么是笔记不存在
            return None

        state = re.findall(r"window.__INITIAL_STATE__=({.*})</script>", html)[
            0
        ].replace("undefined", '""')
        if state != "{}":
            note_dict = humps.decamelize(json.loads(state))
            return note_dict["note"]["note_detail_map"][note_id]["note"]
        return None
