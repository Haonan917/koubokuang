import React, { memo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

/**
 * StreamingMarkdown - Remix AI Studio 风格流式 Markdown 渲染
 *
 * 深色背景适配 + 紫色/青色强调色
 */
function StreamingMarkdown({ content, isStreaming = false }) {
  if (!content || !content.trim()) return null;

  return (
    <div className="
      prose prose-sm prose-invert max-w-none
      text-text-secondary leading-relaxed

      prose-headings:text-text-primary prose-headings:font-display prose-headings:font-bold
      prose-h1:text-xl prose-h1:mt-6 prose-h1:mb-4
      prose-h2:text-lg prose-h2:mt-5 prose-h2:mb-3 prose-h2:pb-2 prose-h2:border-b prose-h2:border-border-default
      prose-h3:text-base prose-h3:mt-4 prose-h3:mb-2 prose-h3:text-primary prose-h3:flex prose-h3:items-center prose-h3:gap-3

      prose-p:text-text-secondary prose-p:leading-relaxed prose-p:my-2

      prose-li:text-text-secondary prose-li:my-1
      prose-ul:my-3 prose-ol:my-3
      prose-ul:marker:text-primary prose-ol:marker:text-primary

      prose-strong:text-text-primary prose-strong:font-semibold
      prose-em:text-text-secondary prose-em:italic

      prose-code:text-accent prose-code:bg-accent/10 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded-md prose-code:text-xs prose-code:font-mono
      prose-pre:bg-bg-tertiary prose-pre:rounded-xl prose-pre:p-4 prose-pre:my-4 prose-pre:border prose-pre:border-border-default

      prose-a:text-accent prose-a:no-underline hover:prose-a:underline hover:prose-a:text-accent/80

      prose-blockquote:border-l-primary prose-blockquote:border-l-2 prose-blockquote:bg-bg-tertiary prose-blockquote:py-2 prose-blockquote:px-4 prose-blockquote:my-4 prose-blockquote:rounded-r-lg prose-blockquote:text-text-secondary prose-blockquote:italic

      prose-hr:border-border-default prose-hr:my-6

      prose-table:border-collapse prose-table:rounded-2xl prose-table:overflow-hidden prose-table:border prose-table:border-border-default
      prose-th:bg-bg-tertiary prose-th:text-text-muted prose-th:font-bold prose-th:text-[10px] prose-th:uppercase prose-th:px-6 prose-th:py-4 prose-th:border-b prose-th:border-border-default
      prose-td:px-6 prose-td:py-4 prose-td:border-b prose-td:border-border-default prose-td:text-text-secondary

      prose-img:rounded-xl prose-img:my-4
    ">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>
        {content}
      </ReactMarkdown>
      {isStreaming && (
        <span className="inline-block w-2 h-5 bg-primary ml-1 animate-pulse rounded-sm" />
      )}
    </div>
  );
}

export default memo(StreamingMarkdown);
