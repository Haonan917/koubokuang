from typing import Any, Dict, List, Optional

from constant.kuaishou import KUAISHOU_API
from models.base_model import ContentTypeEnum
from models.content_detail import (
    AuthorInfo,
    Content,
    ContentDetailResponse,
    InteractionInfo,
)
from models.creator import CreatorContentListResponse, CreatorQueryResponse


class KuaishouExtractor:

    def extract_creator_info(self, response: Dict) -> Optional[CreatorQueryResponse]:
        """
        提取快手创作者信息

        Args:
            response (Dict): 快手创作者信息API响应

        Returns:
            CreatorQueryResponse: 创作者信息
        """
        vision_profile = response.get("visionProfile", {})
        if not vision_profile or vision_profile.get("result") != 1:
            return None

        user_profile = vision_profile.get("userProfile", {})
        if not user_profile:
            return None

        profile = user_profile.get("profile", {})
        owner_count = user_profile.get("ownerCount", {})

        return CreatorQueryResponse(
            nickname=profile.get("user_name", ""),
            user_id=profile.get("user_id", ""),
            avatar=profile.get("headurl", ""),
            description=profile.get("user_text", ""),
            follower_count=str(owner_count.get("fan", 0)),
            following_count=str(owner_count.get("follow", 0)),
            content_count=str(owner_count.get("photo_public", 0)),
        )

    def _extract_video_download_url(self, photo_item: Dict) -> str:
        """
        提取视频下载地址

        Args:
            photo_item (Dict): 快手视频信息

        Returns:
            str: 视频下载地址
        """
        # 优先使用H265编码的视频
        if photo_item.get("photoH265Url"):
            return photo_item.get("photoH265Url")
        
        # 其次使用普通视频URL
        if photo_item.get("photoUrl"):
            return photo_item.get("photoUrl")
        
        # 尝试从videoResource中提取
        video_resource = photo_item.get("videoResource", {})
        if video_resource and isinstance(video_resource, dict):
            # 优先使用hevc编码
            hevc_resource = video_resource.get("hevc", {})
            if hevc_resource and hevc_resource.get("adaptationSet"):
                adaptation_sets = hevc_resource.get("adaptationSet", [])
                if adaptation_sets and len(adaptation_sets) > 0:
                    representations = adaptation_sets[0].get("representation", [])
                    if representations and len(representations) > 0:
                        return representations[0].get("url", "")
            
            # 其次使用h264编码
            h264_resource = video_resource.get("h264", {})
            if h264_resource and h264_resource.get("adaptationSet"):
                adaptation_sets = h264_resource.get("adaptationSet", [])
                if adaptation_sets and len(adaptation_sets) > 0:
                    representations = adaptation_sets[0].get("representation", [])
                    if representations and len(representations) > 0:
                        return representations[0].get("url", "")
        
        return ""

    def _extract_content_cover_url(self, photo_item: Dict) -> str:
        """
        提取内容封面地址

        Args:
            photo_item (Dict): 快手视频信息

        Returns:
            str: 封面地址
        """
        # 优先使用coverUrl
        if photo_item.get("coverUrl"):
            return photo_item.get("coverUrl")
        
        # 其次使用coverUrls中的第一个
        cover_urls = photo_item.get("coverUrls", [])
        if cover_urls and len(cover_urls) > 0:
            return cover_urls[0].get("url", "")
        
        # 最后使用动画封面
        if photo_item.get("animatedCoverUrl"):
            return photo_item.get("animatedCoverUrl")
        
        return ""

    def _extract_content_title(self, photo_item: Dict) -> str:
        """
        提取内容标题

        Args:
            photo_item (Dict): 快手视频信息

        Returns:
            str: 内容标题
        """
        # 对于不同的接口，字段名可能不同
        # 列表接口：originCaption, caption
        # 详情接口：caption
        title = (photo_item.get("originCaption", "") or 
                photo_item.get("caption", ""))
        # 如果都没有，使用视频ID作为标题
        if not title:
            title = f"快手视频_{photo_item.get('id', 'unknown')}"
        return title[:1024] if title else ""

    def _extract_author_info(self, feed_item: Dict) -> AuthorInfo:
        """
        提取作者信息

        Args:
            feed_item (Dict): 快手内容feed项

        Returns:
            AuthorInfo: 作者信息
        """
        author_data = feed_item.get("author", {})
        user_id = author_data.get("id", "")
        return AuthorInfo(
            user_id=user_id,
            nickname=author_data.get("name", ""),
            avatar=author_data.get("headerUrl", ""),
            profile_url=f"https://www.kuaishou.com/profile/{user_id}" if user_id else "",
        )

    def _extract_interaction_info(self, photo_item: Dict) -> InteractionInfo:
        """
        提取互动数据

        Args:
            photo_item (Dict): 快手视频信息

        Returns:
            InteractionInfo: 互动数据
        """
        # 优先使用 realLikeCount（精确数字），否则使用 likeCount（格式化字符串如"18.4万"）
        liked_count = photo_item.get("realLikeCount") or photo_item.get("likeCount", "")
        return InteractionInfo(
            liked_count=str(liked_count),
            play_count=str(photo_item.get("viewCount", "")),
        )

    def _extract_content_detail(self, feed_item: Dict) -> Optional[Content]:
        """
        提取内容详情

        Args:
            feed_item (Dict): 快手内容feed项

        Returns:
            Content: 内容详情
        """
        photo_item = feed_item.get("photo", {})
        if not photo_item or not photo_item.get("id"):
            return None

        # 快手主要是短视频内容
        content_type = ContentTypeEnum.VIDEO

        content_id = photo_item.get("id")
        content = Content(
            id=content_id,
            title=self._extract_content_title(photo_item),
            desc=photo_item.get("caption", "") or "",
            url=f"https://www.kuaishou.com/short-video/{content_id}",
            content_type=content_type,
            cover_url=self._extract_content_cover_url(photo_item),
            image_urls=None,  # 快手主要是视频，暂不处理图片
            video_download_url=self._extract_video_download_url(photo_item),
            author=self._extract_author_info(feed_item),
            interaction=self._extract_interaction_info(photo_item),
        )

        return content

    def extract_contents(self, response: Dict) -> CreatorContentListResponse:
        """
        提取快手内容列表

        Args:
            response (Dict): 快手内容列表API响应

        Returns:
            CreatorContentListResponse: 创作者内容列表响应
        """
        res_contents: List[Content] = []
        
        vision_profile_photo_list = response.get("visionProfilePhotoList", {})
        if not vision_profile_photo_list or vision_profile_photo_list.get("result") != 1:
            return CreatorContentListResponse(
                contents=[],
                has_more=False,
                next_cursor="",
            )

        feeds = vision_profile_photo_list.get("feeds", [])
        pcursor = vision_profile_photo_list.get("pcursor", "")
        has_more = pcursor != "no_more" and pcursor != ""

        for feed_item in feeds:
            content_detail: Optional[Content] = self._extract_content_detail(feed_item)
            if not content_detail:
                continue
            res_contents.append(content_detail)

        return CreatorContentListResponse(
            contents=res_contents,
            has_more=has_more,
            next_cursor=pcursor,
        )

    def extract_content_detail(self, response: Dict) -> Optional[ContentDetailResponse]:
        """
        提取快手内容详情

        Args:
            response (Dict): 快手内容详情API响应

        Returns:
            ContentDetailResponse: 内容详情响应
        """
        if not response:
            return None

        vision_video_detail = response.get("visionVideoDetail", {})
        if not vision_video_detail or vision_video_detail.get("status") != 1:
            return None

        photo_item = vision_video_detail.get("photo", {})
        author_item = vision_video_detail.get("author", {})
        if not photo_item or not photo_item.get("id"):
            return None

        # 构造feed格式的数据以复用提取逻辑
        feed_item = {
            "photo": photo_item,
            "author": author_item,
            "type": "NORMAL"
        }

        content_detail: Optional[Content] = self._extract_content_detail(feed_item)
        if not content_detail:
            return None

        return ContentDetailResponse(
            content=content_detail,
        )