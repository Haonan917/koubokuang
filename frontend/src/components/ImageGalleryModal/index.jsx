import React, { useState } from 'react';
import { ExternalLink, Image as ImageIcon } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import Modal from '../common/Modal';
import ImageCarousel from './ImageCarousel';

/**
 * ImageGalleryModal - 图片轮播对话框
 *
 * 支持:
 * - 图片轮播展示
 * - 图片计数器
 * - mixed 类型时显示"观看视频"链接
 */
function ImageGalleryModal({
  isOpen,
  onClose,
  images,
  title,
  originalUrl,
  videoUrl,
}) {
  const { t } = useTranslation();
  const [currentIndex, setCurrentIndex] = useState(0);

  const totalImages = images?.length || 0;

  // 重置 index 当 modal 关闭时
  const handleClose = () => {
    setCurrentIndex(0);
    onClose();
  };

  // 外部链接按钮
  const headerActions = (
    <div className="flex items-center gap-2">
      {/* 图片计数器 */}
      {totalImages > 0 && (
        <span className="image-modal-counter">
          {currentIndex + 1} / {totalImages}
        </span>
      )}
      {/* 原始链接 */}
      {originalUrl && (
        <a
          href={originalUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="video-modal-external-link"
        >
          <ExternalLink size={16} />
          <span>Original</span>
        </a>
      )}
    </div>
  );

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title={title || t('imageGallery.title', 'Image Gallery')}
      headerActions={headerActions}
      maxWidth="4xl"
    >
      <div className="image-modal-body">
        {/* 图片轮播区域 */}
        <div className="image-modal-carousel-wrapper">
          {totalImages > 0 ? (
            <ImageCarousel
              images={images}
              currentIndex={currentIndex}
              onIndexChange={setCurrentIndex}
            />
          ) : (
            <div className="image-modal-no-images">
              <div className="image-modal-no-images-icon">
                <ImageIcon size={48} />
              </div>
              <p className="image-modal-no-images-text">
                {t('imageGallery.noImages', 'No images available')}
              </p>
            </div>
          )}
        </div>

        {/* Mixed 类型时显示视频链接 */}
        {videoUrl && (
          <div className="image-modal-video-link">
            <a
              href={videoUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="image-modal-watch-video"
            >
              <span className="material-symbols-outlined text-lg">
                play_circle
              </span>
              <span>{t('imageGallery.watchVideo', 'Watch Video')}</span>
              <ExternalLink size={14} />
            </a>
          </div>
        )}
      </div>
    </Modal>
  );
}

export default ImageGalleryModal;
