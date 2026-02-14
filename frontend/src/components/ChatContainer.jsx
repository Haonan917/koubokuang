import React, { useEffect, useRef, forwardRef, useImperativeHandle, memo } from 'react';
import { useTranslation } from 'react-i18next';
import { MessageItem } from './MessageItem';

/**
 * ChatContainer - Remix AI Studio 风格内容容器
 *
 * 显示分析报告和消息列表
 */
export const ChatContainer = memo(forwardRef(({
  messages,
  streamingMessage,
  loading,
  showEmptyState = true,
  onRetry,
}, ref) => {
  const { t } = useTranslation();
  const bottomRef = useRef(null);

  const scrollToBottom = () => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useImperativeHandle(ref, () => ({
    scrollToBottom
  }));

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingMessage]);

  const allMessages = [...messages];
  if (streamingMessage) {
    allMessages.push(streamingMessage);
  }

  // 空状态 - 欢迎页面 (OpenClaw Dark Theme)
  if (allMessages.length === 0 && showEmptyState) {
    const platforms = [
      { name: 'xhs', label: t('platforms.xhs'), logo: '/assets/logos/xhs.png' },
      { name: 'dy', label: t('platforms.dy'), logo: '/assets/logos/dy.png' },
      { name: 'bili', label: t('platforms.bili'), logo: '/assets/logos/bili.png' },
      { name: 'ks', label: t('platforms.ks'), logo: '/assets/logos/ks.png' },
    ];

    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] py-12 animate-fade-in">
        {/* Hero Section - Compact & Refined */}
        <div className="text-center max-w-xl mx-auto mb-12">
          {/* Minimal Icon with Glow */}
          <div className="relative inline-flex mb-6">
            <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-primary to-primary-active flex items-center justify-center shadow-[0_4px_30px_rgba(255,59,59,0.3)]">
              <span className="material-symbols-outlined text-white text-2xl">bolt</span>
            </div>
            {/* Subtle glow ring */}
            <div className="absolute -inset-2 rounded-xl bg-primary/10 blur-xl -z-10" />
          </div>

          {/* Title & Subtitle */}
          <h1 className="font-display text-2xl font-bold text-text-primary mb-3 tracking-tight">
            {t('emptyState.title')}
          </h1>
          <p className="text-sm text-text-muted leading-relaxed max-w-md mx-auto">
            {t('emptyState.subtitle')}
          </p>
        </div>

        {/* Features - Horizontal Pills */}
        <div className="flex flex-wrap justify-center gap-3 mb-12">
          {[
            { icon: 'link', label: t('emptyState.multiPlatform') },
            { icon: 'psychology', label: t('emptyState.aiAnalysis') },
            { icon: 'auto_awesome', label: t('emptyState.creativeRemix') },
          ].map((feature, index) => (
            <div
              key={feature.icon}
              className="group flex items-center gap-2.5 px-4 py-2.5 rounded-full bg-bg-secondary border border-border-default hover:border-primary/30 transition-all duration-200 cursor-default"
              style={{ animationDelay: `${index * 80}ms` }}
            >
              <span className="material-symbols-outlined text-base text-primary">
                {feature.icon}
              </span>
              <span className="text-xs font-semibold text-text-secondary">{feature.label}</span>
            </div>
          ))}
        </div>

        {/* Platform Strip - Minimal & Elegant */}
        <div className="w-full max-w-md">
          {/* Label */}
          <p className="text-[10px] font-bold text-text-muted uppercase tracking-[0.2em] text-center mb-5">
            {t('emptyState.supportedPlatforms')}
          </p>

          {/* Platform Chips Row */}
          <div className="flex justify-center gap-2">
            {platforms.map((platform, index) => (
              <div
                key={platform.name}
                className="group relative flex items-center gap-2.5 px-3.5 py-2.5 rounded-xl bg-bg-secondary border border-border-default hover:bg-bg-tertiary hover:border-primary/20 transition-all duration-200 cursor-default"
                style={{ animationDelay: `${200 + index * 60}ms` }}
              >
                {/* Logo */}
                <div className="w-5 h-5 rounded overflow-hidden flex-shrink-0">
                  <img
                    src={platform.logo}
                    alt={platform.label}
                    className="w-full h-full object-contain opacity-70 group-hover:opacity-100 transition-opacity"
                  />
                </div>
                {/* Name */}
                <span className="text-xs font-medium text-text-muted group-hover:text-text-secondary transition-colors">
                  {platform.label}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // 消息列表 / 报告内容
  return (
    <div
      role="log"
      aria-label="Analysis content"
      aria-live="polite"
      className="flex flex-col gap-10"
    >
      {allMessages.map((msg, index) => {
        // 为 AI 消息提供重试回调（重试时重新发送前一条用户消息）
        const isAI = msg.role === 'assistant';
        const handleRetry = isAI && onRetry ? () => onRetry(index) : undefined;

        return (
          <MessageItem
            key={msg.id}
            message={msg}
            onRetry={handleRetry}
          />
        );
      })}

      {/* 加载指示器 */}
      {loading && !streamingMessage && (
        <div className="flex items-center justify-center gap-3 py-8">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-primary animate-bounce" />
            <div className="w-2 h-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: '0.1s' }} />
            <div className="w-2 h-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: '0.2s' }} />
          </div>
          <span className="text-sm text-text-muted">{t('emptyState.analyzing')}</span>
        </div>
      )}

      {/* 滚动锚点 */}
      <div ref={bottomRef} className="h-4" />
    </div>
  );
}));

ChatContainer.displayName = 'ChatContainer';
