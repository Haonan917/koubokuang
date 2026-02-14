import React, { memo } from 'react';
import { useTranslation } from 'react-i18next';

// 平台 Logo 路径映射
const PLATFORM_LOGOS = {
  xhs: '/assets/logos/xhs.png',
  xiaohongshu: '/assets/logos/xhs.png',
  dy: '/assets/logos/dy.png',
  douyin: '/assets/logos/dy.png',
  bili: '/assets/logos/bili.png',
  bilibili: '/assets/logos/bili.png',
  ks: '/assets/logos/ks.png',
  kuaishou: '/assets/logos/ks.png',
};

/**
 * VideoCard - 视频/图文信息卡片
 *
 * Remix AI Studio 风格的内容展示卡片
 * 包含缩略图、平台标签、标题和统计数据
 * 点击触发外部回调（由父组件控制 modal）
 *
 * @param {Object} contentInfo - 内容信息
 * @param {boolean} showPlayButton - 是否显示播放按钮（视频类型）
 * @param {boolean} showImageIndicator - 是否显示图片数量徽章（图文类型）
 * @param {number} imageCount - 图片数量
 * @param {Function} onClick - 点击回调
 */
function VideoCard({
  contentInfo,
  showPlayButton = true,
  showImageIndicator = false,
  imageCount = 0,
  onClick,
}) {
  const { t } = useTranslation();

  if (!contentInfo) return null;

  const {
    title,
    desc,
    cover_url,
    video_url,
    original_url,
    local_cover_url,
    local_video_url,
    platform,
    duration,
    like_count,
    liked_count = like_count,
    collect_count,
    collected_count = collect_count,
    share_count,
    comment_count,
    view_count,
  } = contentInfo;

  // 优先使用本地 URL
  const displayCoverUrl = local_cover_url || cover_url;

  // 解析可能包含中文单位的数字（防御性措施，后端已处理）
  const parseChineseNumber = (value) => {
    if (typeof value === 'number') return value;
    if (!value) return 0;

    const str = String(value).trim().replace(/,/g, '');
    let multiplier = 1;
    let numStr = str;

    if (str.includes('亿')) {
      multiplier = 100000000;
      numStr = str.replace('亿', '');
    } else if (str.includes('万')) {
      multiplier = 10000;
      numStr = str.replace('万', '');
    }

    const num = parseFloat(numStr);
    return isNaN(num) ? 0 : Math.round(num * multiplier);
  };

  // 格式化数字（保留一位小数的 k 格式）
  const formatNumber = (num) => {
    const parsed = parseChineseNumber(num);
    if (parsed === 0 && num !== 0 && num !== '0') return '-';
    if (parsed >= 1000000) {
      return (parsed / 1000000).toFixed(1) + 'M';
    }
    if (parsed >= 1000) {
      return (parsed / 1000).toFixed(1) + 'k';
    }
    return parsed.toString();
  };

  // 格式化时长
  const formatDuration = (seconds) => {
    if (!seconds) return null;
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // 统计数据 - 播放数只有 B站 显示
  const stats = [
    ...(platform === 'bilibili' ? [{ value: view_count, label: t('videoCard.views') }] : []),
    { value: liked_count, label: t('videoCard.likes') },
    { value: collected_count, label: t('videoCard.saves') },
    { value: share_count, label: t('videoCard.shares') },
    { value: comment_count, label: t('videoCard.comments') },
  ];

  const handleClick = (e) => {
    e.preventDefault();
    onClick?.();
  };

  return (
    <section className="video-preview-card animate-fade-in">
      <div className="video-preview-layout">
        {/* Left: Thumbnail */}
        <div
          className="video-preview-thumbnail"
          style={{ cursor: onClick ? 'pointer' : 'default' }}
          onClick={onClick ? handleClick : undefined}
        >
          {displayCoverUrl ? (
            <img
              src={displayCoverUrl}
              alt={title || t('videoCard.noPreview')}
              className="w-full h-full object-contain"
              onError={(e) => {
                e.target.style.display = 'none';
                e.target.nextSibling?.classList.remove('hidden');
              }}
            />
          ) : null}
          <div className={`absolute inset-0 bg-card-dark flex items-center justify-center ${displayCoverUrl ? 'hidden' : ''}`}>
            <span className="text-text-muted text-sm">{t('videoCard.noPreview')}</span>
          </div>

          {/* 视频：显示播放按钮 */}
          {showPlayButton && (
            <div className="video-preview-overlay">
              <button
                onClick={handleClick}
                className="video-preview-play"
                aria-label={t('videoCard.playVideo')}
              >
                <span className="material-symbols-outlined fill-1">play_arrow</span>
              </button>
            </div>
          )}

          {/* 图文：显示图片数量徽章 */}
          {showImageIndicator && imageCount > 0 && (
            <div className="video-preview-gallery-badge">
              <span className="material-symbols-outlined text-sm">photo_library</span>
              <span>{imageCount}</span>
            </div>
          )}

          {/* 视频才显示时长 */}
          {showPlayButton && duration && (
            <div className="video-preview-duration">
              {formatDuration(duration)}
            </div>
          )}
        </div>

        {/* Right: Info */}
        <div className="video-preview-info">
          <div>
            {/* Meta: Platform + Type */}
            <div className="video-preview-meta">
              {platform && (
                <div className="video-preview-platform">
                  {PLATFORM_LOGOS[platform] ? (
                    <img
                      src={PLATFORM_LOGOS[platform]}
                      alt={t(`platforms.${platform}`, { defaultValue: platform })}
                      className="w-4 h-4 object-contain"
                    />
                  ) : (
                    <span className="material-symbols-outlined text-xs">
                      {showPlayButton ? 'movie' : 'image'}
                    </span>
                  )}
                  {t(`platforms.${platform}`, { defaultValue: platform })}
                </div>
              )}
              <span className="video-preview-type">{t('videoCard.originalAnalysis')}</span>
            </div>

            {/* Title */}
            <h2 className="video-preview-title">
              {title || t('videoCard.untitled')}
            </h2>
          </div>

          {/* Stats Grid */}
          <div className="video-preview-stats">
            {stats.map((stat, i) => (
              <div key={i} className="video-preview-stat">
                <p className="video-preview-stat-value">
                  {formatNumber(stat.value)}
                </p>
                <p className="video-preview-stat-label">{stat.label}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

export default memo(VideoCard);
