/**
 * 聊天 Hook - 管理对话消息和会话状态
 *
 * 重构版本：
 * - 使用 eventHandlers 模块处理 SSE 事件
 * - 使用 formatters 模块生成消息 ID
 * - 使用函数式 setState 减少依赖
 * - 修复竞争条件：同步添加消息，延迟触发 session 回调
 */
import { useState, useCallback, useRef, useEffect } from 'react';
import { sendChatMessage, getSessionMessages, checkLLMConfigStatus } from '../services/api';
import { resolveChatPreferredPayload } from '../utils/chatPreferences';
import { processEvent, finalizeSegments, extractStructuredData } from './chat/eventHandlers';
import { generateMessageId, truncateText } from '../utils/formatters';

/**
 * 创建用户消息对象
 */
function createUserMessage(text, attachments = []) {
  return {
    id: generateMessageId(),
    role: 'user',
    content: text,
    attachments,
    timestamp: Date.now(),
  };
}

/**
 * 创建初始的流式消息对象
 */
function createInitialStreamingMessage() {
  return {
    id: generateMessageId(),
    role: 'assistant',
    segments: [],
    timestamp: Date.now(),
    isComplete: false,
    finalReportStarted: false,  // 是否收到 final_report_start 事件
  };
}

/**
 * 将 API 返回的消息映射为前端格式
 *
 * 支持从 segments_json 恢复完整的消息结构（包括 thinking、tool_call 等）
 */
function mapMessagesFromAPI(messages) {
  return messages.map(msg => {
    // 如果有 segments_json，使用它恢复完整结构
    let segments = [];
    if (msg.segments_json && Array.isArray(msg.segments_json)) {
      segments = msg.segments_json.map(seg => ({
        ...seg,
        // 确保 thinking 和 tool_call 有 status: 'completed'
        status: seg.status || 'completed',
      }));
    } else if (msg.role === 'assistant' && msg.content) {
      // 降级：没有 segments_json 时，将 content 作为 markdown
      segments = [{ type: 'markdown', content: msg.content }];
    }

    return {
      id: msg.id,
      role: msg.role,
      content: msg.content,
      segments,
      timestamp: new Date(msg.timestamp).getTime(),
      isComplete: true, // 历史消息都是完成状态
    };
  });
}

/**
 * 聊天 Hook
 *
 * @param {string} token - Auth token (暂未使用)
 * @param {object} options - 配置选项
 * @param {string} options.currentSessionId - 当前会话 ID（由 useConversations 提供）
 * @param {function} options.onSessionCreated - 新会话创建回调
 * @param {function} options.onSessionUpdated - 会话更新回调
 */
export function useChat(token, options = {}) {
  const { currentSessionId = null, onSessionCreated, onSessionUpdated } = options;

  const [messages, setMessages] = useState([]);
  const [streamingMessage, setStreamingMessage] = useState(null);
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState(currentSessionId);

  // 防止重复请求（React StrictMode 会双重调用）
  const requestInProgressRef = useRef(false);
  // AbortController 用于取消请求
  const abortControllerRef = useRef(null);
  // 当前请求 ID，用于忽略过期的 SSE 事件
  const activeRequestIdRef = useRef(null);
  // 标记刚创建的会话，避免 useEffect 覆盖本地消息
  const justCreatedSessionRef = useRef(null);

  // 同步外部 currentSessionId 变化
  useEffect(() => {
    if (currentSessionId !== sessionId) {
      // 切换会话时中断正在进行的流，避免旧输出串到新会话
      abortControllerRef.current?.abort();
      requestInProgressRef.current = false;
      activeRequestIdRef.current = null;
      setLoading(false);
      setSessionId(currentSessionId);
      setStreamingMessage(null);
    }
  }, [currentSessionId, sessionId]);

  // 加载历史消息
  useEffect(() => {
    if (!currentSessionId) {
      setMessages([]);
      return;
    }

    // 跳过刚创建的会话，避免 API 返回空数据覆盖本地消息
    if (justCreatedSessionRef.current === currentSessionId) {
      justCreatedSessionRef.current = null;
      return;
    }

    let cancelled = false;

    getSessionMessages(currentSessionId, 200, 0)
      .then(data => {
        if (cancelled || !data?.messages) return;
        setMessages(mapMessagesFromAPI(data.messages));
      })
      .catch(error => {
        console.error('Failed to load session messages:', error);
        if (!cancelled) {
          setMessages([]);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [currentSessionId]);

  /**
   * 发送消息
   * @param {string} text - 消息文本
   * @param {Array} attachments - 附件列表
   * @param {object} options - 可选参数 { mode }
   */
  const sendMessage = useCallback(async (text, attachments = [], options = {}) => {
    // 验证输入
    if (!text.trim() && attachments.length === 0) return;
    // 防止重复请求
    if (requestInProgressRef.current) return;

    requestInProgressRef.current = true;

    // 检查 LLM 配置状态
    try {
      const configStatus = await checkLLMConfigStatus();
      if (!configStatus.configured) {
        requestInProgressRef.current = false;
        handleErrorEvent('尚未配置大模型，请先点击左侧边栏底部的设置按钮，配置并激活一个 LLM。', {
          setMessages,
          setStreamingMessage,
          setLoading,
          requestInProgressRef,
        });
        return;
      }
    } catch (e) {
      // 检查失败时不阻塞，让后端兜底
      console.warn('LLM config status check failed:', e);
    }

    // 取消之前的请求
    abortControllerRef.current?.abort();
    abortControllerRef.current = new AbortController();
    const requestId = generateMessageId();
    activeRequestIdRef.current = requestId;
    const isActiveRequest = () => activeRequestIdRef.current === requestId;

    const isNewConversation = !sessionId;
    const userMessage = createUserMessage(text, attachments);

    // 乐观更新：立即添加用户消息
    setMessages(prev => [...prev, userMessage]);
    setLoading(true);
    setStreamingMessage(createInitialStreamingMessage());

    try {
      // 获取历史消息用于上下文
      const history = messages.slice(-20).map(m => ({
        role: m.role,
        content: m.content,
      }));

      const preferredPayload = resolveChatPreferredPayload();

      await sendChatMessage(
        text,
        token,
        {
          conversationId: sessionId,
          history,
          attachments,
          mode: options.mode,  // 传递 mode 参数
          ...preferredPayload,
        },
        {
          signal: abortControllerRef.current.signal,
          onChunk: (event) => {
            if (!isActiveRequest()) return;
            const { type, data } = event;

            // 处理完成事件
            if (type === 'done') {
              handleDoneEvent(data, {
                isNewConversation,
                text,
                sessionId,
                setSessionId,
                setMessages,
                setStreamingMessage,
                setLoading,
                requestInProgressRef,
                justCreatedSessionRef,
                onSessionCreated,
                onSessionUpdated,
              });
              activeRequestIdRef.current = null;
              return;
            }

            // 处理错误事件
            if (type === 'error') {
              activeRequestIdRef.current = null;
              handleErrorEvent(data?.message || '未知错误', {
                setMessages,
                setStreamingMessage,
                setLoading,
                requestInProgressRef,
              });
              return;
            }

            // 处理流式事件
            setStreamingMessage(prev => processEvent(type, data, prev));
          },
          onError: (error) => {
            if (!isActiveRequest()) return;
            activeRequestIdRef.current = null;
            handleErrorEvent(error.message, {
              setMessages,
              setStreamingMessage,
              setLoading,
              requestInProgressRef,
            });
          },
          // 流结束时的兜底处理
          // 正常情况下 handleDoneEvent 已经处理了 loading 状态
          // 这里处理异常情况：流结束但未收到 done 事件
          onComplete: () => {
            if (!isActiveRequest()) return;
            activeRequestIdRef.current = null;
            setLoading(currentLoading => {
              if (currentLoading) {
                console.warn('[useChat] Stream ended without done event, cleaning up');
              }
              return false;
            });

            setStreamingMessage(current => {
              if (current && !current.isComplete) {
                const finalMessage = {
                  ...finalizeSegments(current),
                  isComplete: true,
                };
                setMessages(prev => {
                  if (prev.some(m => m.id === finalMessage.id)) {
                    return prev;
                  }
                  return [...prev, finalMessage];
                });
              }
              return null;
            });

            requestInProgressRef.current = false;
          },
        }
      );
    } catch (error) {
      // 如果是 AbortError，不需要处理
      if (error.name !== 'AbortError') {
        handleErrorEvent(error.message, {
          setMessages,
          setStreamingMessage,
          setLoading,
          requestInProgressRef,
        });
      }
    }
  }, [sessionId, token, messages, onSessionCreated, onSessionUpdated]);

  /**
   * 清空消息
   */
  const clearMessages = useCallback(() => {
    // 取消正在进行的请求
    abortControllerRef.current?.abort();
    requestInProgressRef.current = false;
    activeRequestIdRef.current = null;
    setLoading(false);
    setMessages([]);
    setStreamingMessage(null);
    setSessionId(null);
  }, []);

  /**
   * 从指定的 AI 消息索引重试（重新发送前一条用户消息）
   * @param {number} aiMessageIndex - AI 消息在 messages 数组中的索引
   *
   * 重要：重试时会清除 session_id 并开始新会话，
   * 因为后端 checkpointer 可能保存了损坏的历史（tool_calls 没有对应的 ToolMessage）
   */
  const retryFromIndex = useCallback((aiMessageIndex) => {
    // 找到这条 AI 消息前面的用户消息
    let userMessageIndex = -1;
    for (let i = aiMessageIndex - 1; i >= 0; i--) {
      if (messages[i].role === 'user') {
        userMessageIndex = i;
        break;
      }
    }

    if (userMessageIndex < 0) {
      console.warn('[useChat] No user message found before AI message at index', aiMessageIndex);
      return;
    }

    const userMessage = messages[userMessageIndex];
    const textToResend = userMessage.content;
    const attachmentsToResend = userMessage.attachments || [];

    // 移除从该用户消息开始的所有后续消息
    setMessages(prev => prev.slice(0, userMessageIndex));

    // 清除 session_id，开始新会话
    // 这样可以避免加载后端 checkpointer 中可能损坏的历史
    setSessionId(null);

    // 延迟发送消息，确保 sessionId 状态已更新
    // 注意：这里无法恢复原始的 mode 参数，因为它没有存储在消息中
    setTimeout(() => {
      sendMessage(textToResend, attachmentsToResend);
    }, 0);
  }, [messages, sendMessage]);

  /**
   * 停止生成
   * 取消当前的 SSE 请求并标记消息为已停止
   */
  const stopGeneration = useCallback(() => {
    // 1. 取消 SSE 请求
    abortControllerRef.current?.abort();
    activeRequestIdRef.current = null;

    // 2. 清理状态
    setLoading(false);
    requestInProgressRef.current = false;

    // 3. 标记流式消息为"已停止"
    setStreamingMessage(current => {
      if (!current) return null;

      const stoppedMessage = {
        ...finalizeSegments(current),
        isStopped: true,
        isComplete: true,
      };

      // 添加到消息历史
      setMessages(prev => {
        // 避免重复添加
        if (prev.some(m => m.id === stoppedMessage.id)) {
          return prev;
        }
        return [...prev, stoppedMessage];
      });

      return null;
    });
  }, []);

  return {
    messages,
    streamingMessage,
    loading,
    sessionId,
    sendMessage,
    clearMessages,
    setSessionId,
    retryFromIndex,
    stopGeneration,
  };
}

/**
 * 处理 done 事件
 *
 * 修复竞争条件：
 * 1. 先同步添加 finalMessage 到 messages
 * 2. 延迟触发 onSessionCreated，避免 useEffect 覆盖消息
 */
function handleDoneEvent(data, ctx) {
  const {
    isNewConversation,
    text,
    setSessionId,
    setMessages,
    setStreamingMessage,
    setLoading,
    requestInProgressRef,
    justCreatedSessionRef,
    onSessionCreated,
    onSessionUpdated,
  } = ctx;

  // 诊断日志：检查 transcript 是否在 done 事件中
  console.log('[handleDoneEvent] transcript:', data?.transcript ?
    `text=${data.transcript.text?.length}, segments=${data.transcript.segments?.length}` : 'null');

  // 提取会话 ID
  const newSessionId = data?.session_id || data?.conversation_id;

  // 1. 先完成流式消息并同步添加到 messages
  setStreamingMessage(current => {
    if (!current) return null;

    const finalMessage = {
      ...finalizeSegments(current),
      structuredData: extractStructuredData(data),
    };

    // 同步添加消息（移除 queueMicrotask 避免竞争条件）
    setMessages(prev => {
      // 防止重复添加
      if (prev.some(m => m.id === finalMessage.id)) {
        return prev;
      }
      return [...prev, finalMessage];
    });

    return null;
  });

  // 2. 设置 loading = false
  setLoading(false);
  requestInProgressRef.current = false;

  // 3. 延迟处理 session 相关逻辑，确保消息已经渲染
  if (newSessionId) {
    setSessionId(newSessionId);

    if (isNewConversation && onSessionCreated) {
      // 标记新创建的会话，避免 useEffect 覆盖消息
      if (justCreatedSessionRef) {
        justCreatedSessionRef.current = newSessionId;
      }

      // 延迟触发 onSessionCreated，避免立即触发 useEffect 覆盖消息
      setTimeout(() => {
        onSessionCreated({
          session_id: newSessionId,
          title: truncateText(text, 30),
          first_message: text,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        });
      }, 50);
    } else if (onSessionUpdated) {
      onSessionUpdated(newSessionId);
    }
  }
}

/**
 * 处理错误事件
 */
function handleErrorEvent(errorMessage, ctx) {
  const {
    setMessages,
    setStreamingMessage,
    setLoading,
    requestInProgressRef,
  } = ctx;

  console.error('Chat error:', errorMessage);

  const messageText = `错误: ${errorMessage || '请稍后重试'}`;

  setMessages(prev => [
    ...prev,
    {
      id: generateMessageId(),
      role: 'assistant',
      content: messageText,
      segments: [{ type: 'markdown', content: messageText, status: 'completed' }],
      timestamp: Date.now(),
    },
  ]);

  setStreamingMessage(null);
  setLoading(false);
  requestInProgressRef.current = false;
}
