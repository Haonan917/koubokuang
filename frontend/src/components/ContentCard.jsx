import React, { memo, useState } from 'react';
import VideoCard from './VideoCard';
import VideoPlayerModal from './VideoPlayerModal';
import ImageGalleryModal from './ImageGalleryModal';

/**
 * 解析内容类型
 * @param {string} content_type - 原始内容类型字段
 * @param {boolean} hasVideo - 是否有视频
 * @param {boolean} hasImages - 是否有图片
 * @returns {{ normalizedType: string, isVideoContent: boolean, isImageContent: boolean, isMixedContent: boolean }}
 */
function parseContentType(content_type, hasVideo, hasImages) {
  let normalizedType = null;

  if (content_type) {
    // 处理枚举值（可能是 "ContentType.VIDEO" 或 "video"）
    normalizedType = String(content_type).toLowerCase().replace('contenttype.', '');
  } else {
    // 回退逻辑：根据可用数据推断
    if (hasImages && hasVideo) {
      // 同时有图片和视频，视为 mixed 类型
      normalizedType = 'mixed';
    } else if (hasImages) {
      normalizedType = 'image';
    } else if (hasVideo) {
      normalizedType = 'video';
    } else {
      // 默认视为视频内容（保持向后兼容）
      normalizedType = 'video';
    }
  }

  return {
    normalizedType,
    isVideoContent: normalizedType === 'video',
    isImageContent: normalizedType === 'image' || normalizedType === 'mixed',
    isMixedContent: normalizedType === 'mixed',
  };
}

/**
 * ContentCard - 统一内容卡片组件
 *
 * 根据 content_type 决定展示逻辑:
 * - video: 显示播放按钮，点击弹出视频播放器
 * - image: 显示图片数量徽章，点击弹出图片轮播
 * - mixed: 显示图片数量徽章，点击弹出图片轮播 + "观看视频"链接
 *
 * @param {Object} contentInfo - 内容信息对象
 */
function ContentCard({ contentInfo }) {
  const [isModalOpen, setIsModalOpen] = useState(false);

  if (!contentInfo) return null;

  const {
    title,
    content_type,
    cover_url,
    video_url,
    original_url,
    local_cover_url,
    local_video_url,
    image_urls = [],
  } = contentInfo;

  // 判断是否有视频和图片
  const hasVideo = Boolean(video_url || local_video_url);
  const hasImages = Array.isArray(image_urls) && image_urls.length > 0;

  // 解析内容类型
  const { isVideoContent, isImageContent, isMixedContent } = parseContentType(
    content_type,
    hasVideo,
    hasImages
  );

  // 获取图片列表（fallback 到 cover_url）
  const getImages = () => {
    if (image_urls && image_urls.length > 0) {
      return image_urls;
    }
    // 如果没有 image_urls 但有 cover_url，作为单张图片展示
    if (cover_url || local_cover_url) {
      return [local_cover_url || cover_url];
    }
    return [];
  };

  const images = getImages();
  const displayCoverUrl = local_cover_url || cover_url;

  const handleOpenModal = () => {
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
  };

  return (
    <>
      <VideoCard
        contentInfo={contentInfo}
        showPlayButton={isVideoContent}
        showImageIndicator={isImageContent && images.length > 0}
        imageCount={images.length}
        onClick={handleOpenModal}
      />

      {/* 视频播放器 Modal */}
      {isVideoContent && (
        <VideoPlayerModal
          isOpen={isModalOpen}
          onClose={handleCloseModal}
          title={title}
          localVideoUrl={local_video_url}
          originalVideoUrl={original_url || video_url}
          coverUrl={displayCoverUrl}
        />
      )}

      {/* 图片轮播 Modal */}
      {isImageContent && (
        <ImageGalleryModal
          isOpen={isModalOpen}
          onClose={handleCloseModal}
          images={images}
          title={title}
          originalUrl={original_url}
          // 仅 mixed 类型才传入视频链接
          videoUrl={isMixedContent ? (video_url || original_url) : null}
        />
      )}
    </>
  );
}

export default memo(ContentCard);
