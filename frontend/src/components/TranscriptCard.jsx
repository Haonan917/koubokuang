import React, { useState, memo, useMemo } from 'react';
import { useTranslation } from 'react-i18next';

/**
 * 格式化秒数为时间字符串 (MM:SS 或 H:MM:SS)
 */
function formatTimestamp(seconds) {
  if (typeof seconds !== 'number' || isNaN(seconds)) {
    return '0:00';
  }

  const totalSeconds = Math.floor(seconds);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const secs = totalSeconds % 60;

  if (hours > 0) {
    return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
  return `${minutes}:${secs.toString().padStart(2, '0')}`;
}

/**
 * TranscriptCard - 转录文本卡片
 *
 * 支持两种数据格式：
 * 1. 字符串格式（旧）: "[0:00] 文本内容..."
 * 2. 结构化格式（新）: { text: "...", segments: [{start, end, text}, ...] }
 *
 * 功能：
 * - 带时间戳的时间线展示
 * - 默认折叠，显示前 3 段
 * - 点击展开查看完整字幕
 */
function TranscriptCard({ transcript, segments: propsSegments }) {
  const { t } = useTranslation();
  const [isExpanded, setIsExpanded] = useState(false);

  // 解析转录数据，统一为 segments 数组格式
  const segments = useMemo(() => {
    // 如果直接传入了 segments 数组
    if (propsSegments && Array.isArray(propsSegments) && propsSegments.length > 0) {
      return propsSegments.map(seg => ({
        start: seg.start,
        end: seg.end,
        text: seg.text,
        timestamp: formatTimestamp(seg.start),
      }));
    }

    // 如果 transcript 是对象且包含 segments
    if (transcript && typeof transcript === 'object') {
      if (transcript.segments && Array.isArray(transcript.segments) && transcript.segments.length > 0) {
        return transcript.segments.map(seg => ({
          start: seg.start,
          end: seg.end,
          text: seg.text,
          timestamp: formatTimestamp(seg.start),
        }));
      }
      // 只有 text，没有 segments
      if (transcript.text) {
        return parseTextTranscript(transcript.text);
      }
    }

    // 如果是字符串格式
    if (typeof transcript === 'string' && transcript.trim()) {
      return parseTextTranscript(transcript);
    }

    return [];
  }, [transcript, propsSegments]);

  // 解析字符串格式的转录（兼容旧格式）
  function parseTextTranscript(text) {
    const result = [];
    // 尝试解析 [0:00] 格式
    const regex = /\[(\d+:\d+(?::\d+)?)\]\s*([^\[]*)/g;
    let match;

    while ((match = regex.exec(text)) !== null) {
      const timeStr = match[1];
      const content = match[2].trim();
      if (content) {
        // 解析时间字符串为秒数
        const parts = timeStr.split(':').map(Number);
        let seconds = 0;
        if (parts.length === 3) {
          seconds = parts[0] * 3600 + parts[1] * 60 + parts[2];
        } else if (parts.length === 2) {
          seconds = parts[0] * 60 + parts[1];
        }
        result.push({
          start: seconds,
          text: content,
          timestamp: timeStr,
        });
      }
    }

    // 如果没有匹配到时间戳，按段落分割
    if (result.length === 0) {
      const paragraphs = text.split(/\n+/).filter(p => p.trim());
      paragraphs.forEach((p, i) => {
        result.push({
          start: i * 10, // 估算时间
          text: p.trim(),
          timestamp: formatTimestamp(i * 10),
        });
      });
    }

    // 如果还是空的，作为单段处理
    if (result.length === 0 && text.trim()) {
      result.push({
        start: 0,
        text: text.trim(),
        timestamp: '0:00',
      });
    }

    return result;
  }

  if (segments.length === 0) return null;

  // 默认显示前 3 段
  const previewCount = 3;
  const displaySegments = isExpanded ? segments : segments.slice(0, previewCount);
  const hasMore = segments.length > previewCount;
  const hiddenCount = segments.length - previewCount;

  return (
    <section className="transcript-card animate-fade-in">
      {/* Header */}
      <div className="transcript-header">
        <div className="transcript-title">
          <span className="material-symbols-outlined text-lg">subtitles</span>
          <span>{t('transcript.title')}</span>
          <span className="text-text-muted text-xs ml-2">
            {t('transcript.segments', { count: segments.length })}
          </span>
        </div>
        {hasMore && (
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="transcript-action"
          >
            {isExpanded ? t('transcript.collapse') : t('transcript.viewAll', { count: hiddenCount })}
            <span className="material-symbols-outlined text-sm">
              {isExpanded ? 'expand_less' : 'expand_more'}
            </span>
          </button>
        )}
      </div>

      {/* Content - Timeline Style */}
      <div className={`transcript-content custom-scrollbar ${isExpanded ? 'max-h-96' : 'max-h-48'}`}>
        <div className="transcript-timeline">
          {displaySegments.map((segment, index) => (
            <div key={index} className="transcript-segment group">
              {/* Timeline marker */}
              <div className="transcript-marker">
                <div className="marker-dot" />
                {index < displaySegments.length - 1 && <div className="marker-line" />}
              </div>

              {/* Content */}
              <div className="transcript-segment-content">
                <span className="transcript-timestamp">
                  {segment.timestamp}
                </span>
                <p className="transcript-text">
                  {segment.text}
                </p>
              </div>
            </div>
          ))}
        </div>

        {/* Fade overlay when collapsed */}
        {!isExpanded && hasMore && (
          <div className="transcript-fade-overlay" />
        )}
      </div>
    </section>
  );
}

export default memo(TranscriptCard);
