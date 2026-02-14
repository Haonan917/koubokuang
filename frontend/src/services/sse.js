/**
 * SSE 流处理模块
 * 统一的 Server-Sent Events 处理逻辑
 *
 * 整合原 api.js 和 remixService.js 中的重复代码
 */
import { getCurrentLanguage } from '../i18n';
import { getAccessToken } from './auth';

/**
 * 解析单个 SSE 事件块
 * @param {string} part - SSE 事件块文本
 * @returns {{type: string, data: object}|null}
 */
function parseSSEEvent(part) {
  const lines = part.split(/\n/);
  let eventType = 'message';
  let data = '';

  for (const line of lines) {
    if (line.startsWith('event:')) {
      eventType = line.slice(6).trim();
    } else if (line.startsWith('data:')) {
      // 支持多行 data（标准 SSE 规范）
      const dataPart = line.slice(5).trim();
      if (data) {
        data += '\n' + dataPart;
      } else {
        data = dataPart;
      }
    }
  }

  if (!data) return null;

  // 处理 SSE 标准终止信号 [DONE]（Vercel AI SDK / OpenAI 标准）
  if (data === '[DONE]') {
    return {
      type: 'done',
      data: { finished: true },
    };
  }

  try {
    return {
      type: eventType,
      data: JSON.parse(data),
    };
  } catch (e) {
    console.error('[SSE] JSON parse error:', e, data);
    return null;
  }
}

/**
 * 创建 SSE 流连接
 *
 * @param {string} url - 请求 URL
 * @param {object} body - 请求体（将被 JSON 序列化）
 * @param {object} options - 配置选项
 * @param {AbortSignal} [options.signal] - AbortController signal 用于取消请求
 * @param {function} [options.onChunk] - 收到事件块时的回调 ({type, data})
 * @param {function} [options.onError] - 发生错误时的回调 (error)
 * @param {function} [options.onComplete] - 流结束时的回调
 * @param {object} [options.headers] - 额外的请求头
 * @returns {Promise<void>}
 *
 * @example
 * const controller = new AbortController();
 * await createSSEStream('/api/chat', { message: 'hello' }, {
 *   signal: controller.signal,
 *   onChunk: ({ type, data }) => console.log(type, data),
 *   onError: (err) => console.error(err),
 *   onComplete: () => console.log('done'),
 * });
 * // 取消请求
 * controller.abort();
 */
export async function createSSEStream(url, body, options = {}) {
  const {
    signal,
    onChunk,
    onError,
    onComplete,
    headers = {},
  } = options;

  try {
    // Add Accept-Language header for i18n support
    const language = getCurrentLanguage();

    const token = getAccessToken();
    const authHeader = token ? { Authorization: `Bearer ${token}` } : {};

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept-Language': language,
        ...authHeader,
        ...headers,
      },
      body: JSON.stringify(body),
      signal,
    });

    if (!response.ok) {
      // 尝试解析错误详情
      let errorMessage = `HTTP error! status: ${response.status}`;
      try {
        const errorData = await response.json();
        errorMessage = errorData.detail || errorData.message || errorMessage;
      } catch {
        // 忽略 JSON 解析错误
      }
      throw new Error(errorMessage);
    }

    if (!response.body) {
      throw new Error('Response body is null');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();

      if (done) {
        // 处理缓冲区中剩余的内容
        if (buffer.trim()) {
          const event = parseSSEEvent(buffer);
          if (event) {
            onChunk?.(event);
          }
        }
        onComplete?.();
        break;
      }

      buffer += decoder.decode(value, { stream: true });

      // SSE 格式: event: xxx\ndata: {...}\n\n
      // 按双换行符分割获取完整的事件块
      const parts = buffer.split(/\n\s*\n/);
      buffer = parts.pop() || ''; // 保留不完整的部分

      for (const part of parts) {
        if (!part.trim()) continue;

        const event = parseSSEEvent(part);
        if (event) {
          // 调试日志（可选）
          if (process.env.NODE_ENV === 'development') {
            if (event.type === 'content_chunk' && event.data?.content) {
              console.debug(`[SSE] ${event.type} (${event.data.content.length} chars)`);
            }
          }
          onChunk?.(event);
        }
      }
    }
  } catch (error) {
    // AbortError 是正常的取消操作，不需要报错
    if (error.name === 'AbortError') {
      console.log('[SSE] Request aborted');
      return;
    }

    onError?.(error);
    throw error;
  }
}

/**
 * 创建带有 AbortController 的 SSE 流
 * 返回取消函数，方便组件卸载时清理
 *
 * @param {string} url - 请求 URL
 * @param {object} body - 请求体
 * @param {object} callbacks - 回调函数 {onChunk, onError, onComplete}
 * @returns {{promise: Promise<void>, abort: function}} - promise 和取消函数
 *
 * @example
 * const { promise, abort } = createCancellableSSEStream('/api/chat', { message: 'hi' }, {
 *   onChunk: (event) => console.log(event),
 * });
 *
 * // 组件卸载时取消
 * useEffect(() => () => abort(), []);
 */
export function createCancellableSSEStream(url, body, callbacks = {}) {
  const controller = new AbortController();

  const promise = createSSEStream(url, body, {
    ...callbacks,
    signal: controller.signal,
  });

  return {
    promise,
    abort: () => controller.abort(),
  };
}
