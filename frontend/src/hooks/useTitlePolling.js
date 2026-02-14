/**
 * 标题轮询 Hook - 用于检测会话标题更新
 *
 * 当新会话创建后，后端会异步生成智能标题。
 * 此 Hook 负责轮询检测标题变化并通知更新。
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import { fetchSessions } from '../services/api';

/**
 * 标题轮询 Hook
 *
 * @param {string} sessionId - 要监听的会话 ID
 * @param {string} initialTitle - 初始标题（用于对比检测变化）
 * @param {function} onTitleUpdate - 标题更新回调 (newTitle) => void
 * @param {object} options - 配置选项
 * @param {number} options.delay - 首次轮询延迟（毫秒），默认 3000
 * @param {number} options.interval - 轮询间隔（毫秒），默认 2000
 * @param {number} options.maxRetries - 最大重试次数，默认 3
 * @param {boolean} options.enabled - 是否启用轮询，默认 true
 */
export function useTitlePolling(
  sessionId,
  initialTitle,
  onTitleUpdate,
  options = {}
) {
  const {
    delay = 3000,
    interval = 2000,
    maxRetries = 3,
    enabled = true,
  } = options;

  const [isPolling, setIsPolling] = useState(false);
  const retriesRef = useRef(0);
  const timeoutRef = useRef(null);
  const intervalRef = useRef(null);
  const initialTitleRef = useRef(initialTitle);

  // 更新 initialTitle 的引用
  useEffect(() => {
    initialTitleRef.current = initialTitle;
  }, [initialTitle]);

  // 停止轮询的函数
  const stopPolling = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    setIsPolling(false);
    retriesRef.current = 0;
  }, []);

  // 执行单次轮询检查
  const checkTitle = useCallback(async () => {
    if (!sessionId) return false;

    try {
      // 获取最近的会话列表，找到目标会话
      const data = await fetchSessions(20, 0);
      const sessions = data?.sessions || [];
      const session = sessions.find(s => s.session_id === sessionId);

      if (session && session.title) {
        // 对比标题是否变化
        const currentTitle = session.title;
        const initial = initialTitleRef.current;

        // 检测标题是否已更新（不再是截断的消息）
        // 判断条件：新标题与初始标题不同，且不是简单的截断
        if (currentTitle !== initial && !initial?.startsWith(currentTitle)) {
          // 标题已更新
          if (onTitleUpdate) {
            onTitleUpdate(currentTitle);
          }
          return true; // 成功，停止轮询
        }
      }
    } catch (error) {
      console.warn('Title polling error:', error);
    }

    return false; // 继续轮询
  }, [sessionId, onTitleUpdate]);

  // 开始轮询
  const startPolling = useCallback(() => {
    if (!sessionId || !enabled) return;

    // 清理之前的定时器
    stopPolling();

    setIsPolling(true);
    retriesRef.current = 0;

    // 延迟后开始轮询
    timeoutRef.current = setTimeout(() => {
      // 立即执行一次检查
      checkTitle().then(success => {
        if (success) {
          stopPolling();
          return;
        }

        // 设置轮询间隔
        intervalRef.current = setInterval(async () => {
          retriesRef.current += 1;

          const success = await checkTitle();

          if (success || retriesRef.current >= maxRetries) {
            stopPolling();
          }
        }, interval);
      });
    }, delay);
  }, [sessionId, enabled, delay, interval, maxRetries, checkTitle, stopPolling]);

  // 当 sessionId 变化时重置状态
  useEffect(() => {
    stopPolling();
  }, [sessionId, stopPolling]);

  // 组件卸载时清理
  useEffect(() => {
    return () => stopPolling();
  }, [stopPolling]);

  return {
    isPolling,
    startPolling,
    stopPolling,
  };
}

export default useTitlePolling;
