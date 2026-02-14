import React from 'react';
import { CheckCircle, AlertCircle, FolderOpen, ExternalLink } from 'lucide-react';
import { useTranslation } from 'react-i18next';

/**
 * DownloadStatus - 下载状态显示组件
 *
 * 显示视频下载完成状态或未下载提示
 */
function DownloadStatus({ localVideoUrl, originalVideoUrl, fileSize }) {
  const { t } = useTranslation();

  // 从 URL 中提取文件路径
  const getDisplayPath = (url) => {
    if (!url) return null;
    // 处理本地文件路径，截取后半部分显示
    const parts = url.split('/');
    if (parts.length > 3) {
      return '.../' + parts.slice(-3).join('/');
    }
    return url;
  };

  // 格式化文件大小
  const formatFileSize = (bytes) => {
    if (!bytes) return null;
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  if (localVideoUrl) {
    return (
      <div className="download-status download-status-success">
        <div className="download-status-icon">
          <CheckCircle size={16} className="text-accent-green" />
        </div>
        <div className="download-status-content">
          <span className="download-status-label">{t('videoPlayer.downloaded')}</span>
          {fileSize && (
            <span className="download-status-size">{formatFileSize(fileSize)}</span>
          )}
          <span className="download-status-path" title={localVideoUrl}>
            <FolderOpen size={12} />
            {getDisplayPath(localVideoUrl)}
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="download-status download-status-pending">
      <div className="download-status-icon">
        <AlertCircle size={16} className="text-accent-orange" />
      </div>
      <div className="download-status-content">
        <span className="download-status-label">{t('videoPlayer.notDownloaded')}</span>
        {originalVideoUrl && (
          <a
            href={originalVideoUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="download-status-link"
          >
            <ExternalLink size={12} />
            {t('videoPlayer.openOriginal')}
          </a>
        )}
      </div>
    </div>
  );
}

export default DownloadStatus;
