/**
 * copyToMarkdown.js - Markdown 转换和复制工具
 *
 * 将消息内容转换为 Markdown 格式并复制到剪贴板
 */

import i18next from 'i18next';

/**
 * 用户消息转 Markdown
 * @param {string} content - 用户消息内容
 * @returns {string} Markdown 格式文本
 */
export function userMessageToMarkdown(content) {
  return content || '';
}

/**
 * 格式化数字（保留一位小数的 k/M 格式）
 * @param {number} num
 * @returns {string}
 */
function formatNumber(num) {
  if (!num && num !== 0) return '-';
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + 'M';
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'k';
  }
  return num.toString();
}

/**
 * 格式化时长（秒 -> MM:SS 或 H:MM:SS）
 * @param {number} seconds
 * @returns {string}
 */
function formatDuration(seconds) {
  if (!seconds) return '';
  const totalSeconds = Math.floor(seconds);
  const hours = Math.floor(totalSeconds / 3600);
  const mins = Math.floor((totalSeconds % 3600) / 60);
  const secs = totalSeconds % 60;

  if (hours > 0) {
    return `${hours}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

/**
 * 格式化时间戳
 * @param {number} seconds
 * @returns {string}
 */
function formatTimestamp(seconds) {
  if (typeof seconds !== 'number' || isNaN(seconds)) {
    return '0:00';
  }
  return formatDuration(seconds);
}

/**
 * VideoCard 内容转 Markdown
 * @param {object} contentInfo - 视频/内容信息对象
 * @returns {string} Markdown 格式文本
 */
export function videoCardToMarkdown(contentInfo) {
  if (!contentInfo) return '';

  const {
    title,
    desc,
    platform,
    duration,
    original_url,
    video_url,
    like_count,
    liked_count = like_count,
    collect_count,
    collected_count = collect_count,
    share_count,
    comment_count,
    view_count,
  } = contentInfo;

  const lines = [];

  // 标题
  lines.push(`## ${title || i18next.t('videoCard.untitled')}`);
  lines.push('');

  // 元数据行
  const metaParts = [];
  if (platform) {
    metaParts.push(`**${i18next.t('markdown.platform')}:** ${platform}`);
  }
  if (duration) {
    metaParts.push(`**${i18next.t('markdown.duration')}:** ${formatDuration(duration)}`);
  }
  if (metaParts.length > 0) {
    lines.push(metaParts.join(' | '));
    lines.push('');
  }

  // 统计表格
  const hasStats = view_count || liked_count || collected_count || share_count || comment_count;
  if (hasStats) {
    lines.push(`| ${i18next.t('videoCard.views')} | ${i18next.t('videoCard.likes')} | ${i18next.t('videoCard.saves')} | ${i18next.t('videoCard.shares')} | ${i18next.t('videoCard.comments')} |`);
    lines.push('|-------|-------|-------|--------|----------|');
    lines.push(`| ${formatNumber(view_count)} | ${formatNumber(liked_count)} | ${formatNumber(collected_count)} | ${formatNumber(share_count)} | ${formatNumber(comment_count)} |`);
    lines.push('');
  }

  // 描述
  if (desc) {
    lines.push('> ' + desc.split('\n').join('\n> '));
    lines.push('');
  }

  // 原始链接
  const sourceUrl = original_url || video_url;
  if (sourceUrl) {
    lines.push(`[${i18next.t('markdown.viewOriginal')}](${sourceUrl})`);
    lines.push('');
  }

  return lines.join('\n');
}

/**
 * 转录内容转 Markdown
 * @param {string|object} transcript - 转录文本或对象
 * @param {Array} segments - 转录片段数组（可选）
 * @returns {string} Markdown 格式文本
 */
export function transcriptToMarkdown(transcript, segments) {
  const lines = [];
  lines.push(`## ${i18next.t('transcript.title')}`);
  lines.push('');

  // 解析 segments
  let parsedSegments = [];

  // 如果直接传入了 segments 数组
  if (segments && Array.isArray(segments) && segments.length > 0) {
    parsedSegments = segments;
  }
  // 如果 transcript 是对象且包含 segments
  else if (transcript && typeof transcript === 'object') {
    if (transcript.segments && Array.isArray(transcript.segments) && transcript.segments.length > 0) {
      parsedSegments = transcript.segments;
    } else if (transcript.text) {
      // 只有 text，没有 segments
      lines.push(transcript.text);
      return lines.join('\n');
    }
  }
  // 如果是字符串格式
  else if (typeof transcript === 'string' && transcript.trim()) {
    // 尝试解析 [0:00] 格式
    const regex = /\[(\d+:\d+(?::\d+)?)\]\s*([^\[]*)/g;
    let match;
    while ((match = regex.exec(transcript)) !== null) {
      const timeStr = match[1];
      const content = match[2].trim();
      if (content) {
        parsedSegments.push({ timestamp: timeStr, text: content });
      }
    }
    // 如果没有匹配到，直接返回原文
    if (parsedSegments.length === 0) {
      lines.push(transcript);
      return lines.join('\n');
    }
  }

  // 输出带时间戳的格式
  if (parsedSegments.length > 0) {
    for (const seg of parsedSegments) {
      const timestamp = seg.timestamp || formatTimestamp(seg.start);
      lines.push(`**[${timestamp}]** ${seg.text}`);
      lines.push('');
    }
  }

  return lines.join('\n');
}

/**
 * AI 消息转 Markdown
 * @param {Array} segments - AI 消息的 segments 数组
 * @param {object} structuredData - 结构化数据（可选）
 * @returns {string} Markdown 格式文本
 */
export function aiMessageToMarkdown(segments, structuredData) {
  const lines = [];

  // 提取 content_info segment
  const contentInfoSegment = segments.find(s => s.type === 'content_info');
  const contentInfo = contentInfoSegment?.data;

  // 获取 transcript
  const transcriptSegment = segments.find(s => s.type === 'transcript');
  const transcriptData =
    transcriptSegment?.data ||
    transcriptSegment?.content ||
    contentInfo?.transcript ||
    structuredData?.transcript;
  const transcriptSegments = transcriptData?.segments || null;
  const transcript = transcriptData?.text || (typeof transcriptData === 'string' ? transcriptData : null);

  // 过滤出内容类型的 segments（text 和 markdown）
  const contentSegments = segments.filter(s => s.type === 'text' || s.type === 'markdown');

  // VideoCard 内容
  if (contentInfo) {
    lines.push(videoCardToMarkdown(contentInfo));
    lines.push('---');
    lines.push('');
  }

  // Transcript 内容
  if (transcript || transcriptSegments) {
    lines.push(transcriptToMarkdown(transcript, transcriptSegments));
    lines.push('---');
    lines.push('');
  }

  // Markdown/Text 内容
  for (const segment of contentSegments) {
    if (segment.type === 'markdown' && segment.content) {
      lines.push(segment.content);
      lines.push('');
    } else if (segment.type === 'text' && segment.content) {
      lines.push(segment.content);
      lines.push('');
    }
  }

  return lines.join('\n').trim();
}

/**
 * 复制文本到剪贴板（含降级方案）
 * @param {string} text - 要复制的文本
 * @returns {Promise<boolean>} 是否复制成功
 */
export async function copyToClipboard(text) {
  // 优先使用 Clipboard API
  if (navigator.clipboard && navigator.clipboard.writeText) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch (err) {
      console.warn('Clipboard API failed, falling back to execCommand:', err);
    }
  }

  // 降级方案：使用 execCommand
  try {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.left = '-9999px';
    textarea.style.top = '-9999px';
    document.body.appendChild(textarea);
    textarea.focus();
    textarea.select();

    const success = document.execCommand('copy');
    document.body.removeChild(textarea);
    return success;
  } catch (err) {
    console.error('Copy failed:', err);
    return false;
  }
}
