import { useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { getSessionState } from '../services/api';

/**
 * Session 路由同步 Hook
 *
 * 负责:
 * - 从 URL 解析 session ID
 * - URL 变化时验证并同步到应用状态
 * - 应用状态变化时同步到 URL
 * - 处理无效 session ID 重定向
 *
 * @param {object} options
 * @param {string|null} options.currentId - 当前选中的会话 ID
 * @param {function} options.setCurrentId - 设置当前会话 ID
 * @param {Array} options.conversations - 会话列表
 * @param {boolean} options.conversationsLoaded - 会话列表是否已加载
 */
export function useSessionRouter({
  currentId,
  setCurrentId,
  conversations,
  conversationsLoaded,
}) {
  const { sessionId: urlSessionId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();

  // 用于防止循环更新的标记
  const isNavigatingRef = useRef(false);
  const lastUrlSessionIdRef = useRef(null);

  // 导航到首页（新会话）
  const navigateToHome = useCallback(() => {
    isNavigatingRef.current = true;
    navigate('/', { replace: true });
    setTimeout(() => {
      isNavigatingRef.current = false;
    }, 0);
  }, [navigate]);

  // 导航到特定会话
  const navigateToSession = useCallback((sessionId) => {
    if (!sessionId) {
      navigateToHome();
      return;
    }
    isNavigatingRef.current = true;
    navigate(`/session/${sessionId}`, { replace: false });
    setTimeout(() => {
      isNavigatingRef.current = false;
    }, 0);
  }, [navigate, navigateToHome]);

  // URL 变化时同步到应用状态
  useEffect(() => {
    // 如果是由我们触发的导航，跳过
    if (isNavigatingRef.current) {
      return;
    }

    // 如果 URL 没有变化，跳过
    if (urlSessionId === lastUrlSessionIdRef.current) {
      return;
    }
    lastUrlSessionIdRef.current = urlSessionId;

    // 等待会话列表加载完成
    if (!conversationsLoaded) {
      return;
    }

    // URL 中没有 sessionId，清空当前会话
    if (!urlSessionId) {
      if (currentId !== null) {
        setCurrentId(null);
      }
      return;
    }

    // URL 中有 sessionId，验证并同步
    const validateAndSync = async () => {
      // 先检查本地会话列表
      const existsLocally = conversations.some(
        c => c.session_id === urlSessionId
      );

      if (existsLocally) {
        // 本地存在，直接同步
        if (currentId !== urlSessionId) {
          setCurrentId(urlSessionId);
        }
        return;
      }

      // 本地不存在，向后端验证
      try {
        const sessionState = await getSessionState(urlSessionId);
        if (sessionState) {
          // 后端存在，同步状态
          if (currentId !== urlSessionId) {
            setCurrentId(urlSessionId);
          }
        } else {
          // 后端不存在，重定向到首页
          console.warn(`Session ${urlSessionId} not found, redirecting to home`);
          navigateToHome();
        }
      } catch (error) {
        console.error('Failed to validate session:', error);
        // 验证失败，重定向到首页
        navigateToHome();
      }
    };

    validateAndSync();
  }, [
    urlSessionId,
    currentId,
    setCurrentId,
    conversations,
    conversationsLoaded,
    navigateToHome,
  ]);

  // 应用状态变化时同步到 URL（当用户通过侧边栏切换会话时）
  // 注意：这个 effect 只在 currentId 由应用内部改变时触发
  // 如果是由 URL 变化触发的，上面的 effect 会处理
  useEffect(() => {
    // 如果正在导航中，跳过（防止循环）
    if (isNavigatingRef.current) {
      return;
    }

    // 检查当前 URL 是否已经匹配
    const currentUrlSessionId = location.pathname.startsWith('/session/')
      ? location.pathname.split('/session/')[1]
      : null;

    if (currentId === null && currentUrlSessionId !== null) {
      // 应用状态为空，但 URL 有值，需要导航到首页
      // 但这种情况由 URL 变化 effect 处理
      return;
    }

    if (currentId !== null && currentId !== currentUrlSessionId) {
      // 应用状态有值，但 URL 不匹配，需要更新 URL
      navigateToSession(currentId);
    }
  }, [currentId, location.pathname, navigateToSession]);

  return {
    urlSessionId,
    navigateToHome,
    navigateToSession,
  };
}
