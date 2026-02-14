from typing import Any, Dict, List, Optional

from constant.douyin import DOUYIN_INDEX_URL, DOUYIN_NOTE_TYPE, DOUYIN_VIDEO_TYPE
from models.base_model import ContentTypeEnum
from models.content_detail import (
    AuthorInfo,
    Content,
    ContentDetailResponse,
    InteractionInfo,
)
from models.creator import CreatorContentListResponse, CreatorQueryResponse


class DouyinExtractor:

    def extract_creator_info(self, response: Dict) -> Optional[CreatorQueryResponse]:
        """
        提取抖音主页信息

        Args:
            response (Dict): 抖音用户信息

        Returns:
            CreatorQueryResponse: 创作者信息
        """
        user_info = response.get("user", {})
        if not user_info:
            return None

        return CreatorQueryResponse(
            nickname=user_info.get("nickname"),
            user_id=user_info.get("sec_uid"),
            avatar=user_info.get("avatar_larger", {}).get("url_list", [""])[0],
            description=user_info.get("signature"),
            follower_count=str(user_info.get("max_follower_count")),
            following_count=str(user_info.get("following_count")),
            content_count=str(user_info.get("aweme_count")),
        )

    def _extract_video_download_url(self, video_item: Dict) -> str:
        """
        提取视频下载地址

        Args:
            video_item (Dict): 抖音视频

        Returns:
            str: 视频下载地址
        """
        url_h264_list = video_item.get("play_addr_h264", {}).get("url_list", [])
        url_256_list = video_item.get("play_addr_256", {}).get("url_list", [])
        url_list = video_item.get("play_addr", {}).get("url_list", [])
        actual_url_list = url_h264_list or url_256_list or url_list
        if not actual_url_list or len(actual_url_list) < 2:
            return ""
        return actual_url_list[1]

    def _extract_content_cover_url(self, aweme_detail: Dict) -> str:
        """
        提取视频封面地址

        Args:
            aweme_detail (Dict): 抖音内容详情

        Returns:
            str: 视频封面地址
        """
        res_cover_url = ""

        video_item = aweme_detail.get("video", {})
        raw_cover_url_list = (
            video_item.get("raw_cover", {}) or video_item.get("origin_cover", {})
        ).get("url_list", [])
        if raw_cover_url_list and len(raw_cover_url_list) > 1:
            res_cover_url = raw_cover_url_list[1]

        return res_cover_url

    def _extract_content_image_urls(self, video_item: Dict) -> Optional[List[str]]:
        """
        提取内容图片地址

        Args:
            video_item (Dict): 抖音视频
        """
        res_image_urls: List[str] = []
        images: List[Dict[str, Any]] = video_item.get("images", [])
        if not images:
            return None
        for image_item in images:
            url_list = image_item.get("url_list", [])
            if not url_list or len(url_list) < 2:
                continue
            res_image_urls.append(url_list[1])
        return res_image_urls

    def _extract_content_title(self, video_item: Dict) -> str:
        """
        提取内容标题

        Args:
            video_item (Dict): 抖音视频

        Returns:
            str: 视频标题
        """
        return video_item.get("caption", "")[:1024] or video_item.get("desc", "")[:1024]

    def _extract_author_info(self, aweme_item: Dict) -> AuthorInfo:
        """
        提取作者信息

        Args:
            aweme_item (Dict): 抖音内容

        Returns:
            AuthorInfo: 作者信息
        """
        author_data = aweme_item.get("author", {})
        sec_uid = author_data.get("sec_uid", "")
        return AuthorInfo(
            user_id=str(author_data.get("uid", "")),
            sec_uid=sec_uid,
            nickname=author_data.get("nickname", ""),
            avatar=author_data.get("avatar_thumb", {}).get("url_list", [""])[0],
            profile_url=f"https://www.douyin.com/user/{sec_uid}" if sec_uid else "",
        )

    def _extract_interaction_info(self, aweme_item: Dict) -> InteractionInfo:
        """
        提取互动数据

        Args:
            aweme_item (Dict): 抖音内容

        Returns:
            InteractionInfo: 互动数据
        """
        statistics = aweme_item.get("statistics", {})
        return InteractionInfo(
            liked_count=str(statistics.get("digg_count", "")),
            collected_count=str(statistics.get("collect_count", "")),
            comment_count=str(statistics.get("comment_count", "")),
            share_count=str(statistics.get("share_count", "")),
            play_count=str(statistics.get("play_count", "")),
        )

    def _extract_content_detail(self, aweme_item: Dict) -> Optional[Content]:
        """
        提取内容详情

        Args:
            aweme_item (Dict): 抖音内容

        Returns:
            Content: 内容详情
        """
        if aweme_item.get("aweme_type") == DOUYIN_NOTE_TYPE:
            content_type = ContentTypeEnum.NOTE
        elif aweme_item.get("aweme_type") == DOUYIN_VIDEO_TYPE:
            content_type = ContentTypeEnum.VIDEO
        else:
            return None

        content = Content(
            id=aweme_item.get("aweme_id"),
            title=self._extract_content_title(aweme_item),
            desc=aweme_item.get("desc", ""),
            url=f"{DOUYIN_INDEX_URL}/{content_type.value}/{aweme_item.get('aweme_id')}",
            content_type=content_type,
            cover_url=self._extract_content_cover_url(aweme_item),
            image_urls=self._extract_content_image_urls(aweme_item),
            video_download_url=self._extract_video_download_url(
                aweme_item.get("video", {})
            ),
            author=self._extract_author_info(aweme_item),
            interaction=self._extract_interaction_info(aweme_item),
        )
        if not content.cover_url and content.image_urls:
            content.cover_url = content.image_urls[0]
        return content

    def extract_contents(self, response: Dict) -> CreatorContentListResponse:
        """
        提取抖音内容

        Args:
            response (Dict): 抖音内容

        Returns:
            CreatorContentListResponse: 创作者内容列表响应
        """
        res_contents: List[Content] = []
        aweme_list = response.get("aweme_list", [])
        has_more = response.get("has_more", 0) == 1
        next_cursor = response.get("max_cursor", "")
        for aweme_item in aweme_list:
            content_detail: Optional[Content] = self._extract_content_detail(aweme_item)
            if not content_detail:
                continue
            res_contents.append(content_detail)
        return CreatorContentListResponse(
            contents=res_contents,
            has_more=has_more,
            next_cursor=str(next_cursor),
        )

    def extract_content_detail(self, response: Dict) -> Optional[ContentDetailResponse]:
        """
        提取抖音内容详情
        """

        if not response:
            return None

        aweme_item = response.get("aweme_detail", {})
        if not aweme_item:
            return None

        content_detail: Optional[Content] = self._extract_content_detail(aweme_item)
        if not content_detail:
            return None

        return ContentDetailResponse(
            content=content_detail,
        )
