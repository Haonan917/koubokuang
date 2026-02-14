import React, { memo } from 'react';
import CheckCircle from 'lucide-react/dist/esm/icons/check-circle';
import Loader2 from 'lucide-react/dist/esm/icons/loader-2';
import Circle from 'lucide-react/dist/esm/icons/circle';
import { getToolIcon } from '../constants/tools';
import { useTranslation } from 'react-i18next';

/**
 * ToolCallCard - 深色主题工具调用卡片
 *
 * ViralAI 风格的工具执行状态卡片
 * 青色进行中 + 绿色完成
 *
 * ┌─────────────────────────────┐
 * │ ✓ Completed video analysis  │
 * └─────────────────────────────┘
 *
 * ┌─────────────────────────────┐
 * │ ⟳ Parsing link...          │
 * │   Detecting platform...     │
 * └─────────────────────────────┘
 */
function ToolCallCard({ segment }) {
  const { t } = useTranslation();
  const isRunning = segment.status === 'running';
  const isCompleted = segment.status === 'completed';

  const IconComponent = getToolIcon(segment.tool);
  const label = segment.toolLabel || segment.tool;

  return (
    <div className={`
      my-3 px-4 py-3 rounded-xl border
      transition-all duration-300 animate-fade-in
      ${isRunning
        ? 'bg-accent-cyan/5 border-accent-cyan/30 shadow-[0_0_15px_rgba(6,182,212,0.1)]'
        : 'bg-bg-secondary border-border-default'
      }
    `}>
      <div className="flex items-center gap-3">
        {/* 状态图标 */}
        <div className={`
          w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0
          ${isRunning
            ? 'bg-accent-cyan/20'
            : isCompleted
              ? 'bg-accent-green/20'
              : 'bg-bg-tertiary'
          }
        `}>
          {isRunning ? (
            <Loader2 className="w-4 h-4 animate-spin text-accent-cyan" />
          ) : isCompleted ? (
            <CheckCircle className="w-4 h-4 text-accent-green" />
          ) : (
            <Circle className="w-4 h-4 text-text-muted" />
          )}
        </div>

        {/* 工具信息 */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className={`
              text-sm font-medium
              ${isRunning
                ? 'text-accent-cyan'
                : isCompleted
                  ? 'text-accent-green'
                  : 'text-text-secondary'
              }
            `}>
              {isCompleted ? `✓ ${label}` : label}
            </span>

            {isRunning && (
              <span className="text-xs text-accent-cyan/70 animate-pulse">
                {t('steps.processing')}...
              </span>
            )}
          </div>

          {/* 进度消息 */}
          {isRunning && (segment.progress || segment.message) && (
            <p className="text-xs text-text-muted mt-1 truncate">
              {segment.progress || segment.message}
            </p>
          )}
        </div>

        {/* 工具图标 */}
        <div className="flex-shrink-0">
          <IconComponent className={`
            w-4 h-4
            ${isRunning ? 'text-accent-cyan' : 'text-text-muted'}
          `} />
        </div>
      </div>
    </div>
  );
}

export default memo(ToolCallCard);
