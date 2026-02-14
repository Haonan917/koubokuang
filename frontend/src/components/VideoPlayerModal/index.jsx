import React from 'react';
import { ExternalLink, Video } from 'lucide-react';
import Modal from '../common/Modal';
import VideoPlayer from './VideoPlayer';
import DownloadStatus from './DownloadStatus';

/**
 * VideoPlayerModal - 视频播放对话框
 *
 * 组合 Modal + VideoPlayer + DownloadStatus
 * 支持三种状态：可播放、未下载、加载中
 */
function VideoPlayerModal({
  isOpen,
  onClose,
  title,
  localVideoUrl,
  originalVideoUrl,
  coverUrl,
  fileSize,
}) {
  // 外部链接按钮
  const headerActions = originalVideoUrl ? (
    <a
      href={originalVideoUrl}
      target="_blank"
      rel="noopener noreferrer"
      className="video-modal-external-link"
    >
      <ExternalLink size={16} />
      <span>Original</span>
    </a>
  ) : null;

  // 判断是否可以播放本地视频
  const canPlay = Boolean(localVideoUrl);

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={title || 'Video Player'}
      headerActions={headerActions}
      maxWidth="4xl"
    >
      <div className="video-modal-body">
        {/* Video Player Area */}
        <div className="video-modal-player-wrapper">
          {canPlay ? (
            <VideoPlayer url={localVideoUrl} coverUrl={coverUrl} />
          ) : (
            <div className="video-modal-no-video">
              <div className="video-modal-no-video-icon">
                <Video size={48} />
              </div>
              <p className="video-modal-no-video-text">
                Video not downloaded yet
              </p>
              {originalVideoUrl && (
                <a
                  href={originalVideoUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="video-modal-no-video-link"
                >
                  <ExternalLink size={16} />
                  Watch on original platform
                </a>
              )}
            </div>
          )}
        </div>

        {/* Download Status */}
        <div className="video-modal-status">
          <DownloadStatus
            localVideoUrl={localVideoUrl}
            originalVideoUrl={originalVideoUrl}
            fileSize={fileSize}
          />
        </div>
      </div>
    </Modal>
  );
}

export default VideoPlayerModal;
