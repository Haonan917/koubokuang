import React, { useState, memo, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { formatShortDuration } from '../utils/formatters';
import { getToolLabel } from '../constants/tools';

// 第一性原理：保持事件的原始时间顺序，不按类型分组
// 删除了 sortStepsByToolOrder - 它会打乱 thinking 和 tool_call 的交替顺序

/**
 * 获取步骤的显示名称
 * @param {object} step - 步骤对象
 * @param {Function} t - i18n 翻译函数
 */
function getStepDisplayLabel(step, t) {
  if (step.type === 'tool_call') {
    return getToolLabel(step.tool, false, t) || step.toolLabel || step.tool;
  }
  if (step.type === 'thinking') {
    return t('steps.thinking');
  }
  if (step.type === 'sub_step') {
    return step.label || step.step_id || t('steps.processing');
  }
  if (step.type === 'intent') {
    return step.modeName ? t('steps.mode', { mode: step.modeName }) : t('steps.analyzingIntent');
  }
  return step.toolLabel || t('steps.processing');
}

/**
 * 将步骤按层级组织（工具调用包含子步骤）
 *
 * 使用 parent_tool 字段将 sub_steps 关联到正确的 tool_call，
 * 而不是依赖顺序（因为从数据库加载时 sub_steps 可能在 tool_call 之前）
 */
function organizeStepsWithHierarchy(steps) {
  // 1. 分类所有步骤
  const toolCallMap = new Map(); // tool name -> tool call with subSteps
  const subStepsByParent = new Map(); // parent_tool -> [sub_steps]

  for (const step of steps) {
    if (step.type === 'tool_call') {
      toolCallMap.set(step.tool, { ...step, subSteps: [] });
    } else if (step.type === 'sub_step') {
      const parent = step.parent_tool || 'unknown';
      if (!subStepsByParent.has(parent)) {
        subStepsByParent.set(parent, []);
      }
      subStepsByParent.get(parent).push(step);
    }
  }

  // 2. 将 sub_steps 分配到对应的 tool_call
  for (const [parentTool, subs] of subStepsByParent) {
    if (toolCallMap.has(parentTool)) {
      toolCallMap.get(parentTool).subSteps.push(...subs);
    }
  }

  // 3. 按原始顺序重建结果（跳过已归入 tool_call 的 sub_steps）
  const result = [];

  for (const step of steps) {
    if (step.type === 'tool_call') {
      result.push(toolCallMap.get(step.tool));
    } else if (step.type === 'sub_step') {
      // 检查是否已归入某个 tool_call
      const parent = step.parent_tool;
      if (parent && toolCallMap.has(parent)) {
        // 已归入 tool_call，跳过
        continue;
      }
      // 没有 parent_tool 或 parent 不存在，作为独立步骤
      result.push(step);
    } else {
      result.push(step);
    }
  }

  return result;
}

/**
 * StepsCollapsible - Remix AI Studio 风格可折叠步骤列表
 *
 * Analysis Complete 卡片，包含处理步骤和耗时
 * 支持：
 * - Thinking 内容可折叠展开
 * - 工具调用包含子步骤层级
 */
function StepsCollapsible({ steps = [], isStreaming = false }) {
  const { t } = useTranslation();
  const [isExpanded, setIsExpanded] = useState(true);

  // 过滤有效步骤
  const validSteps = steps.filter(s => {
    if (s.type === 'tool_call' || s.type === 'sub_step' || s.type === 'intent') return true;
    if (s.type === 'thinking') {
      return s.status === 'running' || (s.content && s.content.length > 0);
    }
    if (s.type === 'process_text') {
      return s.content && s.content.trim().length > 0;
    }
    return false;
  });

  if (validSteps.length === 0) return null;

  // 保持原始时间顺序，只组织子步骤层级
  const organizedSteps = organizeStepsWithHierarchy(validSteps);

  // 计算完成状态（包括子步骤）
  const countSteps = (steps) => {
    let total = 0;
    let completed = 0;
    for (const step of steps) {
      if (step.type === 'tool_call' && step.subSteps?.length > 0) {
        // 工具调用本身算一步
        total += 1;
        if (step.status === 'completed') completed += 1;
        // 子步骤也算
        for (const sub of step.subSteps) {
          total += 1;
          if (sub.status === 'completed') completed += 1;
        }
      } else {
        total += 1;
        if (step.status === 'completed') completed += 1;
      }
    }
    return { total, completed };
  };

  const { total: totalCount, completed: completedCount } = countSteps(organizedSteps);
  const isAllCompleted = completedCount === totalCount && !isStreaming;

  return (
    <section className="analysis-progress-card animate-fade-in">
      {/* Header */}
      <div className="analysis-progress-header">
        {/* Status */}
        <div className="analysis-progress-status">
          <span className={`material-symbols-outlined icon ${isAllCompleted ? '' : 'animate-spin'}`}>
            {isAllCompleted ? 'check_circle' : 'progress_activity'}
          </span>
          <span className="text font-display font-bold">
            {isAllCompleted ? t('steps.analysisComplete') : t('steps.analyzing')}
          </span>
        </div>

        {/* Steps count + toggle */}
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="analysis-progress-steps"
        >
          {isAllCompleted
            ? t('steps.stepsCompleted', { count: totalCount })
            : t('steps.stepsProgress', { completed: completedCount, total: totalCount })
          }
          <span className="material-symbols-outlined text-lg">
            {isExpanded ? 'expand_less' : 'expand_more'}
          </span>
        </button>
      </div>

      {/* Steps list */}
      {isExpanded && (
        <div className="analysis-progress-body space-y-3">
          {organizedSteps.map((step, index) => {
            const uniqueKey = `${step.type}-${index}`;
            if (step.type === 'thinking') {
              return <ThinkingStepItem key={uniqueKey} step={step} t={t} />;
            }
            if (step.type === 'tool_call') {
              return <ToolCallStepItem key={uniqueKey} step={step} t={t} />;
            }
            if (step.type === 'process_text') {
              return <ProcessTextItem key={uniqueKey} step={step} />;
            }
            return <StepItem key={uniqueKey} step={step} t={t} />;
          })}
        </div>
      )}
    </section>
  );
}

/**
 * 获取最后一行文本（用于折叠状态显示）
 */
function getLastLine(text, maxLength = 50) {
  if (!text) return '';
  // 按换行分割，取最后一个非空行
  const lines = text.split('\n').filter(line => line.trim());
  const lastLine = lines[lines.length - 1] || text;
  // 如果最后一行太长，取最后 maxLength 个字符
  if (lastLine.length > maxLength) {
    return '...' + lastLine.slice(-maxLength);
  }
  return lastLine;
}

/**
 * Thinking 步骤项 - 支持折叠展开完整内容
 *
 * 特性:
 * - 运行时图标有脉动发光动画
 * - 折叠状态：显示最后一行 + 打字机动画（逐字显示）
 * - 展开状态：显示完整内容，支持换行
 */
const ThinkingStepItem = memo(function ThinkingStepItem({ step, t }) {
  const [isContentExpanded, setIsContentExpanded] = useState(false);
  // 打字机效果：当前显示的字符数
  const [displayedLength, setDisplayedLength] = useState(0);
  const prevContentRef = useRef('');

  const isCompleted = step.status === 'completed';
  const isRunning = step.status === 'running';
  const duration = step.duration;
  const content = step.content || '';

  // 打字机效果：逐字符显示
  useEffect(() => {
    // 如果已完成，直接显示全部
    if (isCompleted) {
      setDisplayedLength(content.length);
      return;
    }

    // 如果内容变化了，从之前的位置继续打字
    if (content !== prevContentRef.current) {
      const prevLen = prevContentRef.current.length;
      prevContentRef.current = content;

      // 如果新内容更长，启动打字机动画
      if (content.length > prevLen) {
        // 先设置为之前的长度，然后逐字增加
        setDisplayedLength(prevLen);

        const targetLength = content.length;
        let currentLen = prevLen;

        const timer = setInterval(() => {
          currentLen += 1;
          if (currentLen >= targetLength) {
            setDisplayedLength(targetLength);
            clearInterval(timer);
          } else {
            setDisplayedLength(currentLen);
          }
        }, 30); // 每 30ms 显示一个字符

        return () => clearInterval(timer);
      }
    }
  }, [content, isCompleted]);

  // 是否需要折叠（超过 50 字符或有换行）
  const needsCollapse = content.length > 50 || content.includes('\n');

  // 当前应该显示的内容（打字机效果）
  const visibleContent = isCompleted ? content : content.slice(0, displayedLength);

  // 折叠时显示最后一行，展开时显示完整内容
  const displayContent = needsCollapse && !isContentExpanded
    ? getLastLine(visibleContent, 50)
    : visibleContent;

  // 是否正在打字（还有字符未显示）
  const isTyping = isRunning && displayedLength < content.length;

  // 图标类名：运行时添加 is-running 触发动画
  const iconClass = `material-symbols-outlined analysis-step-icon thinking ${isRunning ? 'is-running' : ''}`;

  return (
    <div className="analysis-step-expandable">
      <div
        className={`analysis-step ${needsCollapse ? 'cursor-pointer hover:bg-white/5 rounded-lg -mx-2 px-2' : ''}`}
        onClick={needsCollapse ? () => setIsContentExpanded(!isContentExpanded) : undefined}
      >
        <div className="analysis-step-content flex-1 min-w-0">
          <span className={iconClass}>
            psychology
          </span>
          <div className="thinking-text-container text-text-secondary text-sm">
            <span className="text-text-muted">{t('steps.thinking')}: </span>
            {isContentExpanded ? (
              // 展开状态：显示完整内容，支持换行
              <span className="thinking-text-expanded">
                "{visibleContent}"
              </span>
            ) : (
              // 折叠状态：显示最后一行 + 打字机效果
              <span className={`thinking-text-collapsed ${isTyping ? 'thinking-typing' : ''}`}>
                <span className="thinking-text-inner">
                  {displayContent ? `"${displayContent}"` : '...'}
                </span>
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {needsCollapse && (
            <span className="material-symbols-outlined text-text-muted text-base">
              {isContentExpanded ? 'expand_less' : 'expand_more'}
            </span>
          )}
          {duration !== undefined && duration !== null && (
            <span className="analysis-step-duration">
              {formatShortDuration(duration)}
            </span>
          )}
        </div>
      </div>
    </div>
  );
});

/**
 * 过程性文本步骤项
 * 显示工具调用之间的 Agent 说明文字
 */
const ProcessTextItem = memo(function ProcessTextItem({ step }) {
  const content = step.content || '';
  if (!content.trim()) return null;

  // 截取显示（最多 80 字符）
  const displayContent = content.length > 80
    ? content.slice(0, 80) + '...'
    : content;

  return (
    <div className="analysis-step py-1">
      <div className="analysis-step-content">
        <span className="material-symbols-outlined analysis-step-icon text-blue-400/70 text-sm">
          chat_bubble_outline
        </span>
        <span className="text-text-muted text-sm italic">
          "{displayContent}"
        </span>
      </div>
    </div>
  );
});

/**
 * 工具调用步骤项 - 支持子步骤层级
 */
const ToolCallStepItem = memo(function ToolCallStepItem({ step, t }) {
  const [isSubStepsExpanded, setIsSubStepsExpanded] = useState(true);
  const isCompleted = step.status === 'completed';
  const isRunning = step.status === 'running';
  const label = getStepDisplayLabel(step, t);
  const duration = step.duration;
  const hasSubSteps = step.subSteps && step.subSteps.length > 0;

  return (
    <div className="analysis-step-with-children">
      {/* 主步骤 */}
      <div
        className={`analysis-step ${hasSubSteps ? 'cursor-pointer hover:bg-white/5 rounded-lg -mx-2 px-2' : ''}`}
        onClick={hasSubSteps ? () => setIsSubStepsExpanded(!isSubStepsExpanded) : undefined}
      >
        <div className="analysis-step-content">
          <span className={`material-symbols-outlined analysis-step-icon ${isCompleted ? 'completed' : isRunning ? 'thinking animate-spin' : ''}`}>
            {isCompleted ? 'check_circle' : isRunning ? 'progress_activity' : 'radio_button_unchecked'}
          </span>
          <span className="text-text-secondary">
            {label}
            {isRunning && !step.progress && '...'}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {hasSubSteps && (
            <span className="material-symbols-outlined text-text-muted text-base">
              {isSubStepsExpanded ? 'expand_less' : 'expand_more'}
            </span>
          )}
          {duration !== undefined && duration !== null && (
            <span className="analysis-step-duration">
              {formatShortDuration(duration)}
            </span>
          )}
        </div>
      </div>

      {/* 子步骤列表 */}
      {hasSubSteps && isSubStepsExpanded && (
        <div className="ml-6 pl-4 border-l border-border-subtle mt-2 space-y-2">
          {step.subSteps.map((subStep, subIndex) => (
            <SubStepItem key={`sub-${subIndex}`} step={subStep} t={t} />
          ))}
        </div>
      )}
    </div>
  );
});

/**
 * 子步骤项
 */
const SubStepItem = memo(function SubStepItem({ step, t }) {
  const isCompleted = step.status === 'completed';
  const isRunning = step.status === 'running';
  const label = step.label || step.step_id || t('steps.processing');
  const duration = step.duration;
  const message = step.message; // 完成时的消息

  return (
    <div className="analysis-step py-1">
      <div className="analysis-step-content">
        <span className={`material-symbols-outlined text-sm ${isCompleted ? 'text-accent' : isRunning ? 'text-primary animate-spin' : 'text-text-muted'}`}>
          {isCompleted ? 'check' : isRunning ? 'progress_activity' : 'circle'}
        </span>
        <span className="text-text-muted text-sm">
          {label}
          {isRunning && '...'}
          {isCompleted && message && (
            <span className="text-text-secondary ml-1">- {message}</span>
          )}
        </span>
      </div>
      {duration !== undefined && duration !== null && (
        <span className="text-text-muted text-xs">
          {formatShortDuration(duration)}
        </span>
      )}
    </div>
  );
});

/**
 * 普通步骤项
 */
const StepItem = memo(function StepItem({ step, t }) {
  const isCompleted = step.status === 'completed';
  const isRunning = step.status === 'running';
  const label = getStepDisplayLabel(step, t);
  const duration = step.duration;

  return (
    <div className="analysis-step">
      <div className="analysis-step-content">
        <span className={`material-symbols-outlined analysis-step-icon ${isCompleted ? 'completed' : isRunning ? 'thinking animate-spin' : ''}`}>
          {isCompleted ? 'check_circle' : isRunning ? 'progress_activity' : 'radio_button_unchecked'}
        </span>
        <span className="text-text-secondary">
          {label}
          {isRunning && !step.progress && '...'}
        </span>
      </div>
      {duration !== undefined && duration !== null && (
        <span className="analysis-step-duration">
          {formatShortDuration(duration)}
        </span>
      )}
    </div>
  );
});

export default memo(StepsCollapsible);
