import React, { memo, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { copyToClipboard } from '../utils/copyToMarkdown';

/**
 * MessageActions - 消息底部操作栏
 *
 * 显示在 AI 消息底部的操作按钮（复制、重试）
 * 参考 ChatGPT/Claude 的 UI 风格
 *
 * @param {function} getMarkdown - 获取 Markdown 内容的函数
 * @param {function} onRetry - 重试回调（重新发送前一条用户消息）
 * @param {boolean} showRetry - 是否显示重试按钮
 */
function MessageActions({ getMarkdown, onRetry, showRetry = true }) {
  const { t } = useTranslation();
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async (e) => {
    e.preventDefault();
    e.stopPropagation();

    try {
      const content = typeof getMarkdown === 'function' ? getMarkdown() : getMarkdown;
      const success = await copyToClipboard(content);

      if (success) {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      }
    } catch (err) {
      console.error('Copy failed:', err);
    }
  }, [getMarkdown]);

  const handleRetry = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    if (onRetry) {
      onRetry();
    }
  }, [onRetry]);

  return (
    <div className="message-actions">
      {/* 复制按钮 */}
      <button
        onClick={handleCopy}
        className={`message-action-btn ${copied ? 'copied' : ''}`}
        title={copied ? t('message.copied') : t('message.copyMarkdown')}
        aria-label={copied ? t('message.copied') : t('message.copyMarkdown')}
      >
        <span className="material-symbols-outlined">
          {copied ? 'check' : 'content_copy'}
        </span>
      </button>

      {/* 重试按钮 */}
      {showRetry && onRetry && (
        <button
          onClick={handleRetry}
          className="message-action-btn"
          title={t('message.retry')}
          aria-label={t('message.retry')}
        >
          <span className="material-symbols-outlined">refresh</span>
        </button>
      )}
    </div>
  );
}

export default memo(MessageActions);
