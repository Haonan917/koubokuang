/**
 * SSE 事件处理器模块
 * 将 useChat.js 中复杂的事件处理逻辑拆分为独立的纯函数
 *
 * 设计原则：
 * - 每个处理器都是纯函数，接收当前状态和事件数据，返回新状态
 * - 不依赖外部状态，便于测试和维护
 * - 统一的错误处理和边界检查
 *
 * 后端 SSE 事件类型（Vercel AI SDK 标准）：
 * - reasoning_start / reasoning_delta / reasoning_finish - 思考过程
 * - text_delta - 内容流
 * - tool_call_start / tool_call_finish - 工具调用
 * - tool_progress - 工具执行进度
 * - done - 完成
 * - error - 错误
 */
import { getToolInfo } from '../../constants/tools';

/**
 * 查找最后一个符合条件的 segment
 * @param {Array} segments - segments 数组
 * @param {string} type - segment 类型
 * @param {function} predicate - 额外的过滤条件
 * @returns {{segment: object, index: number}|null}
 */
function findLastSegment(segments, type, predicate = () => true) {
  for (let i = segments.length - 1; i >= 0; i--) {
    if (segments[i].type === type && predicate(segments[i])) {
      return { segment: segments[i], index: i };
    }
  }
  return null;
}

/**
 * 追加内容到 markdown segment
 * 如果最后一个 segment 是 markdown 类型则追加，否则创建新的
 */
function appendToMarkdown(segments, content) {
  const newSegments = [...segments];
  const lastSeg = newSegments[newSegments.length - 1];

  if (lastSeg?.type === 'markdown') {
    newSegments[newSegments.length - 1] = {
      ...lastSeg,
      content: lastSeg.content + content,
    };
  } else {
    newSegments.push({
      type: 'markdown',
      content,
    });
  }

  return newSegments;
}

// ========== 事件处理器 ==========

/**
 * 处理 intent_start 事件
 * 创建意图识别 segment
 */
function handleIntentStart(prev, data) {
  if (!prev) return prev;

  return {
    ...prev,
    segments: [
      ...prev.segments,
      {
        type: 'intent',
        status: 'running',
        message: data?.message || '正在分析意图...',
        startTime: Date.now(),
      },
    ],
  };
}

/**
 * 处理 intent_end 事件
 * 更新意图识别结果
 */
function handleIntentEnd(prev, data) {
  if (!prev) return prev;

  const segments = prev.segments.map(seg => {
    if (seg.type === 'intent' && seg.status === 'running') {
      return {
        ...seg,
        status: 'completed',
        mode: data?.mode,
        modeName: data?.mode_name,
        confidence: data?.confidence,
        reasoning: data?.reasoning,
        duration: (Date.now() - seg.startTime) / 1000,
      };
    }
    return seg;
  });

  return { ...prev, segments };
}

/**
 * 处理 final_report_start 事件
 * 标记最终报告开始，后续的 text_delta 将作为最终报告
 */
function handleFinalReportStart(prev, data) {
  if (!prev) return prev;

  return {
    ...prev,
    finalReportStarted: true,
  };
}

/**
 * 处理 content_chunk / text_delta 事件
 * 根据 finalReportStarted 标志决定文本类型
 */
function handleContentChunk(prev, data) {
  if (!prev) return prev;
  const content = data?.content || '';
  if (!content) return prev;

  // 简化：根据 finalReportStarted 判断
  if (!prev.finalReportStarted) {
    // 最终报告未开始 → 过程性文本
    const newSegments = [...prev.segments];
    const lastSeg = newSegments[newSegments.length - 1];

    if (lastSeg?.type === 'process_text') {
      newSegments[newSegments.length - 1] = {
        ...lastSeg,
        content: lastSeg.content + content,
      };
    } else {
      newSegments.push({
        type: 'process_text',
        content,
        status: 'completed',
      });
    }
    return { ...prev, segments: newSegments };
  }

  // 最终报告已开始 → markdown
  return {
    ...prev,
    segments: appendToMarkdown(prev.segments, content),
  };
}


/**
 * 处理 thinking_start 事件
 * 创建新的 thinking segment
 */
function handleThinkingStart(prev, data) {
  if (!prev) return prev;
  const thinkingId = data?.thinking_id;

  // 检查是否已存在相同 ID 的 running thinking segment
  const existing = findLastSegment(prev.segments, 'thinking',
    s => s.thinking_id === thinkingId && s.status === 'running'
  );
  if (existing) {
    return prev; // 已存在，不重复添加
  }

  return {
    ...prev,
    segments: [
      ...prev.segments,
      {
        type: 'thinking',
        thinking_id: thinkingId,
        content: '',
        startTime: Date.now(),
        status: 'running',
      },
    ],
  };
}

/**
 * 处理 thinking_chunk 事件
 * 追加内容到当前 thinking segment
 */
function handleThinkingChunk(prev, data) {
  if (!prev) return prev;
  const thinkingId = data?.thinking_id;
  const content = data?.content || '';

  const segments = prev.segments.map(seg => {
    if (seg.type === 'thinking' && seg.thinking_id === thinkingId && seg.status === 'running') {
      return {
        ...seg,
        content: seg.content + content,
      };
    }
    return seg;
  });

  return { ...prev, segments };
}

/**
 * 处理 thinking_end 事件
 * 标记 thinking segment 完成并计算时长
 */
function handleThinkingEnd(prev, data) {
  if (!prev) return prev;
  const thinkingId = data?.thinking_id;

  const segments = prev.segments.map(seg => {
    if (seg.type === 'thinking' && seg.thinking_id === thinkingId) {
      const duration = seg.startTime ? (Date.now() - seg.startTime) / 1000 : null;
      return {
        ...seg,
        status: 'completed',
        duration,
      };
    }
    return seg;
  });

  return { ...prev, segments };
}

/**
 * 处理 tool_call_start 事件
 * 创建新的 tool_call segment
 */
function handleToolCallStart(prev, data) {
  if (!prev) return prev;
  const tool = data?.tool;
  const toolInfo = getToolInfo(tool);

  return {
    ...prev,
    segments: [
      ...prev.segments,
      {
        type: 'tool_call',
        tool,
        toolLabel: toolInfo.label,
        input: data?.input,
        status: 'running',
      },
    ],
  };
}

/**
 * 处理 tool_call_end 事件
 * 标记 tool_call segment 完成
 */
function handleToolCallEnd(prev, data) {
  if (!prev) return prev;
  const tool = data?.tool;

  const segments = prev.segments.map(seg => {
    if (seg.type === 'tool_call' && seg.tool === tool && seg.status === 'running') {
      return {
        ...seg,
        output: data?.output,
        status: 'completed',
      };
    }
    return seg;
  });

  return { ...prev, segments };
}

/**
 * 处理 tool_progress 事件
 * 更新 tool_call segment 的进度消息
 */
function handleToolProgress(prev, data) {
  if (!prev) return prev;
  const message = data?.message;
  if (!message) return prev;

  const segments = [...prev.segments];
  const found = findLastSegment(segments, 'tool_call', s => s.status === 'running');

  if (found) {
    segments[found.index] = {
      ...found.segment,
      progress: message,
    };
  }

  return { ...prev, segments };
}

/**
 * 处理 sub_step_start 事件
 * 创建新的 sub_step segment，用于工具内部的多阶段处理
 */
function handleSubStepStart(prev, data) {
  if (!prev) return prev;
  const { step_id, label, parent_tool } = data;

  return {
    ...prev,
    segments: [
      ...prev.segments,
      {
        type: 'sub_step',
        step_id,
        label,
        parent_tool,
        status: 'running',
        startTime: Date.now(),
      },
    ],
  };
}

/**
 * 处理 sub_step_end 事件
 * 更新对应子步骤状态为完成
 */
function handleSubStepEnd(prev, data) {
  if (!prev) return prev;
  const { step_id, message } = data;

  const segments = prev.segments.map(seg => {
    if (seg.type === 'sub_step' && seg.step_id === step_id) {
      return {
        ...seg,
        status: 'completed',
        message,
        duration: (Date.now() - seg.startTime) / 1000,
      };
    }
    return seg;
  });

  return { ...prev, segments };
}

/**
 * 处理 content_info 事件
 * 创建 content_info segment 用于展示内容概览卡片
 * 这个事件在 fetch_content 完成后立即发送，让前端可以提前展示内容卡片
 */
function handleContentInfo(prev, data) {
  if (!prev) return prev;
  const contentInfo = data?.content_info;
  if (!contentInfo) return prev;

  // 检查是否已存在 content_info segment，避免重复添加
  const existing = findLastSegment(prev.segments, 'content_info');
  if (existing) {
    // 更新现有的
    const segments = [...prev.segments];
    segments[existing.index] = {
      ...existing.segment,
      data: contentInfo,
    };
    return { ...prev, segments };
  }

  // 创建新的 content_info segment
  return {
    ...prev,
    segments: [
      ...prev.segments,
      {
        type: 'content_info',
        data: contentInfo,
        status: 'completed',
      },
    ],
  };
}

/**
 * 处理 transcript 事件
 * 创建或更新 transcript segment 用于展示视频转录文本和时间戳
 * 这个事件在 process_video 完成后发送
 */
function handleTranscript(prev, data) {
  if (!prev) return prev;
  // data 可能直接是 transcript 对象，也可能是 { transcript: {...} }
  const transcript = data?.transcript || data;
  if (!transcript) return prev;

  // 检查是否已存在 transcript segment，避免重复添加
  const existing = findLastSegment(prev.segments, 'transcript');
  if (existing) {
    // 更新现有的
    const segments = [...prev.segments];
    segments[existing.index] = {
      ...existing.segment,
      data: transcript,
    };
    return { ...prev, segments };
  }

  // 创建新的 transcript segment
  return {
    ...prev,
    segments: [
      ...prev.segments,
      {
        type: 'transcript',
        data: transcript,
        status: 'completed',
      },
    ],
  };
}

// ========== 事件处理器映射 ==========

const eventHandlers = {
  // 意图识别（保持不变）
  intent_start: handleIntentStart,
  intent_end: handleIntentEnd,
  // 最终报告开始信号
  final_report_start: handleFinalReportStart,
  // 内容流（Vercel 标准：text_delta）
  text_delta: handleContentChunk,
  // 思考过程（Vercel 标准：reasoning_*）
  reasoning_start: handleThinkingStart,
  reasoning_delta: handleThinkingChunk,
  reasoning_finish: handleThinkingEnd,
  // 工具调用（Vercel 标准：tool_call_finish）
  tool_call_start: handleToolCallStart,
  tool_call_finish: handleToolCallEnd,
  tool_progress: handleToolProgress,
  // 子步骤（工具内部多阶段处理，保持不变）
  sub_step_start: handleSubStepStart,
  sub_step_end: handleSubStepEnd,
  // 内容信息（保持不变）
  content_info: handleContentInfo,
  // 转录文本（视频处理完成后）
  transcript: handleTranscript,
};

/**
 * 处理 SSE 事件
 * 根据事件类型分发到对应的处理器
 *
 * @param {string} eventType - 事件类型
 * @param {object} data - 事件数据
 * @param {object} currentState - 当前 streamingMessage 状态
 * @returns {object} - 新的 streamingMessage 状态
 */
export function processEvent(eventType, data, currentState) {
  const handler = eventHandlers[eventType];

  if (handler) {
    return handler(currentState, data);
  }

  // 未知事件类型，保持原状态
  if (eventType !== 'done' && eventType !== 'error') {
    console.debug('[eventHandlers] Unhandled event type:', eventType);
  }

  return currentState;
}

/**
 * 标记所有 running 的 segments 为 completed
 * 并处理无工具调用场景下的 process_text → markdown 转换
 *
 * @param {object} state - streamingMessage 状态
 * @returns {object} - 新状态
 */
export function finalizeSegments(state) {
  if (!state) return state;

  // 检查是否有工具调用
  const hasToolCall = state.segments.some(s => s.type === 'tool_call');

  const segments = state.segments.map(seg => {
    // 标记 running 为 completed
    let newSeg = seg.status === 'running' ? { ...seg, status: 'completed' } : seg;

    // 无工具调用场景：将 process_text 转为 markdown（它们实际上是最终报告）
    if (!hasToolCall && newSeg.type === 'process_text') {
      newSeg = { ...newSeg, type: 'markdown' };
    }

    return newSeg;
  });

  return {
    ...state,
    segments,
    isComplete: true,
  };
}

/**
 * 提取结构化数据
 *
 * @param {object} data - done 事件的数据
 * @returns {object|null}
 */
export function extractStructuredData(data) {
  if (!data) return null;

  const {
    content_info,
    transcript,
    analysis,
    copywriting,
    cloned_voice,
    tts_result,
    lipsync_result,
  } = data;
  const result = {
    content_info,
    transcript,
    analysis,
    copywriting,
    cloned_voice,
    tts_result,
    lipsync_result,
  };

  // 如果所有字段都为空，返回 null
  return Object.values(result).some(Boolean) ? result : null;
}
