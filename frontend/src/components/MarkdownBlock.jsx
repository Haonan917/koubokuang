import React, { memo } from 'react';
import StreamingMarkdown from './StreamingMarkdown';

/**
 * MarkdownBlock - AI Report 样式的 Markdown 内容块组件
 *
 * Remix AI Studio 风格的分析报告展示
 * 包含 glass-effect 卡片和标题分割线
 */
function MarkdownBlock({ segment, isStreaming = false, showReportHeader = false }) {
  if (!segment.content) {
    return null;
  }

  return (
    <section className="markdown-container glass-effect p-10 rounded-3xl border border-border-default shadow-2xl animate-fade-in">
      {/* Report header divider */}
      {showReportHeader && (
        <div className="report-section-divider mb-8">
          <div className="line" />
          <h2 className="title">AI Insight Engine Report</h2>
          <div className="line" />
        </div>
      )}

      {/* Markdown content */}
      <StreamingMarkdown
        content={segment.content}
        isStreaming={isStreaming}
      />
    </section>
  );
}

export default memo(MarkdownBlock);
