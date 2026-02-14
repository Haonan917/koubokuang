import React, { useState, memo } from 'react';
import { useTranslation } from 'react-i18next';
import ArrowRight from 'lucide-react/dist/esm/icons/arrow-right';
import LinkIcon from 'lucide-react/dist/esm/icons/link';
import X from 'lucide-react/dist/esm/icons/x';
import Zap from 'lucide-react/dist/esm/icons/zap';

/**
 * LinkInput - 深色主题链接输入
 *
 * ViralAI 风格的独立链接输入页面
 * 渐变标题 + 发光输入框 + 平台标签
 */
function LinkInput({ onStart, loading }) {
  const { t } = useTranslation();
  const [url, setUrl] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!url.trim()) return;
    onStart(url);
  };

  return (
    <div className="w-full max-w-3xl mx-auto p-4 md:p-6 transition-all duration-500 ease-in-out">
      {/* Header */}
      <div className="text-center mb-10">
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-accent-cyan to-accent-purple flex items-center justify-center shadow-lg shadow-accent-cyan/25 mb-6 mx-auto animate-fade-in">
          <Zap className="w-8 h-8 text-white" />
        </div>

        <h2 className="text-3xl md:text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-accent-cyan to-accent-purple mb-4 animate-fade-in" style={{ animationDelay: '0.1s' }}>
          {t('linkInput.title')}
        </h2>

        <p className="text-text-secondary text-sm md:text-base max-w-xl mx-auto animate-fade-in" style={{ animationDelay: '0.2s' }}>
          {t('linkInput.subtitle')}
        </p>
      </div>

      {/* Input Form */}
      <form onSubmit={handleSubmit} className="relative group animate-fade-in" style={{ animationDelay: '0.3s' }}>
        <div className="absolute inset-y-0 left-5 flex items-center pointer-events-none">
          <LinkIcon className="h-5 w-5 text-text-muted group-focus-within:text-accent-cyan transition-colors" />
        </div>

        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder={t('linkInput.placeholder')}
          disabled={loading}
          className="
            w-full bg-bg-secondary backdrop-blur-xl
            border border-border-default rounded-2xl
            py-5 pl-14 pr-36
            text-text-primary placeholder:text-text-muted
            focus:outline-none focus:ring-2 focus:ring-accent-cyan/50 focus:border-accent-cyan/50
            shadow-lg shadow-black/20
            transition-all text-base
            hover:border-border-default/80
          "
        />

        {url && (
          <button
            type="button"
            onClick={() => setUrl('')}
            className="absolute right-32 top-1/2 -translate-y-1/2 p-2 text-text-muted hover:text-text-secondary transition-colors"
          >
            <X size={16} />
          </button>
        )}

        <div className="absolute right-2 top-2 bottom-2">
          <button
            type="submit"
            disabled={!url.trim() || loading}
            className="
              h-full px-6
              bg-gradient-to-r from-accent-cyan to-accent-cyan/80
              hover:from-accent-cyan/90 hover:to-accent-cyan/70
              disabled:opacity-50 disabled:cursor-not-allowed
              text-white rounded-xl font-medium
              transition-all shadow-lg shadow-accent-cyan/25
              hover:shadow-accent-cyan/40
              flex items-center gap-2 group/btn
            "
          >
            {loading ? (
              <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <>
                {t('linkInput.start')}
                <ArrowRight size={18} className="group-hover/btn:translate-x-1 transition-transform" />
              </>
            )}
          </button>
        </div>
      </form>

      {/* Supported Platforms */}
      <div className="mt-10 flex justify-center gap-6 animate-fade-in" style={{ animationDelay: '0.4s' }}>
        {['xhs', 'douyin', 'bilibili', 'kuaishou'].map((platform) => (
          <div
            key={platform}
            className="flex flex-col items-center gap-2 opacity-50 hover:opacity-100 transition-opacity cursor-default"
          >
            <span className="text-xs font-medium uppercase tracking-wider text-text-muted">
              {platform}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default memo(LinkInput);
