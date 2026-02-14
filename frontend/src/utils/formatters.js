/**
 * 格式化工具函数模块
 * 统一管理时间、数字等格式化逻辑
 */

/**
 * 格式化时长显示
 * @param {number|null|undefined} seconds - 秒数
 * @returns {string} 格式化后的时长字符串
 *
 * @example
 * formatDuration(0.5)    // "500ms"
 * formatDuration(1.13)   // "1.13s"
 * formatDuration(65)     // "1分5秒"
 * formatDuration(120)    // "2分"
 */
export function formatDuration(seconds) {
  if (seconds == null) return '';
  if (seconds === 0) return '0';

  // 小于1秒显示毫秒
  if (seconds < 1) {
    return `${Math.round(seconds * 1000)}ms`;
  }

  // 小于60秒显示秒（保留2位小数）
  if (seconds < 60) {
    return `${seconds.toFixed(2)}s`;
  }

  // 60秒以上显示分钟和秒
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);

  if (secs > 0) {
    return `${mins}分${secs}秒`;
  }
  return `${mins}分`;
}

/**
 * 格式化简短时长（用于步骤列表等场景）
 * @param {number|null|undefined} seconds - 秒数
 * @returns {string} 格式化后的简短时长字符串
 *
 * @example
 * formatShortDuration(0.5)    // "500ms"
 * formatShortDuration(1.13)   // "约1sec"
 * formatShortDuration(65)     // "1m5s"
 */
export function formatShortDuration(seconds) {
  if (seconds == null) return '';
  if (seconds === 0) return '0';

  if (seconds < 1) {
    return `${Math.round(seconds * 1000)}ms`;
  }

  if (seconds < 60) {
    return `约${Math.round(seconds)}sec`;
  }

  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);

  if (secs > 0) {
    return `${mins}m${secs}s`;
  }
  return `~${mins}m`;
}

/**
 * 生成唯一消息 ID
 * @returns {string} 格式为 msg_{timestamp}_{random}
 */
export function generateMessageId() {
  return `msg_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;
}

/**
 * 截断文本并添加省略号
 * @param {string} text - 原始文本
 * @param {number} maxLength - 最大长度
 * @returns {string} 截断后的文本
 */
export function truncateText(text, maxLength = 30) {
  if (!text || text.length <= maxLength) return text;
  return text.substring(0, maxLength) + '...';
}
