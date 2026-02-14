import React, { memo } from 'react';
import List from 'lucide-react/dist/esm/icons/list';
import Layers from 'lucide-react/dist/esm/icons/layers';
import Sparkles from 'lucide-react/dist/esm/icons/sparkles';
import Palette from 'lucide-react/dist/esm/icons/palette';
import { MODE_COLOR_CLASSES } from '../constants/modes';

/**
 * QuickActions - 智能快捷操作按钮
 *
 * ViralAI 风格的 4 个主要功能按钮
 * 用于触发不同的内容分析和创作模式
 *
 * 注：这里的 mode id 与 INSIGHT_MODES 略有不同，
 * QUICK_ACTIONS 专注于前端交互预填充，
 * INSIGHT_MODES 对应后端 MODE_PROMPTS。
 */

const QUICK_ACTIONS = [
  {
    id: 'summarize',
    label: 'Summarize',
    subtitle: '精华提炼',
    icon: List,
    prefill: '提炼这个内容的核心要点：',
    placeholder: '[粘贴链接]',
    color: 'cyan',
  },
  {
    id: 'analyze',
    label: 'Deep Analysis',
    subtitle: '深度拆解',
    icon: Layers,
    prefill: '深度拆解这个内容的创作技巧：',
    placeholder: '[粘贴链接]',
    color: 'orange',
  },
  {
    id: 'template',
    label: 'Template',
    subtitle: '模板学习',
    icon: Sparkles,
    prefill: '提取这个内容的可复用模板：',
    placeholder: '[粘贴链接]',
    color: 'pink',
  },
  {
    id: 'style_explore',
    label: 'Style Explore',
    subtitle: '风格探索',
    icon: Palette,
    prefill: '探索这个内容的不同表达风格：',
    placeholder: '[粘贴链接]',
    color: 'purple',
  },
];

function QuickActions({ onSelect, disabled = false }) {
  return (
    <div className="w-full">
      {/* 网格布局 */}
      <div className="quick-actions-grid">
        {QUICK_ACTIONS.map((action, index) => {
          const Icon = action.icon;
          const colors = MODE_COLOR_CLASSES[action.color];

          return (
            <button
              key={action.id}
              onClick={() => onSelect(action)}
              disabled={disabled}
              className={`
                flex items-center gap-3
                p-4 rounded-xl
                bg-bg-secondary
                border border-border-default
                text-left
                transition-all duration-200
                disabled:opacity-50 disabled:cursor-not-allowed
                ${colors.hover}
                animate-fade-in
              `}
              style={{ animationDelay: `${index * 0.05}s` }}
            >
              {/* 图标 */}
              <div className={`
                w-10 h-10 rounded-xl
                flex items-center justify-center
                flex-shrink-0
                ${colors.icon}
                transition-transform group-hover:scale-110
              `}>
                <Icon className="w-5 h-5" />
              </div>

              {/* 文字 */}
              <div className="min-w-0">
                <h3 className="font-semibold text-text-primary text-sm truncate">
                  {action.label}
                </h3>
                <p className="text-xs text-text-muted truncate">
                  {action.subtitle}
                </p>
              </div>
            </button>
          );
        })}
      </div>

      {/* 支持平台提示 */}
      <p className="text-[11px] text-text-muted text-center mt-4">
        Supports Xiaohongshu, Douyin, Bilibili, Kuaishou
      </p>
    </div>
  );
}

export default memo(QuickActions);
