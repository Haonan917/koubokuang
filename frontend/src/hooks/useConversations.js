import { useState, useCallback, useEffect, useMemo } from 'react';
import { fetchSessions, deleteSession as apiDeleteSession } from '../services/api';

/**
 * 会话管理 Hook - 与后端 API 同步
 *
 * 负责:
 * - 从后端加载会话列表
 * - 创建新会话（清空当前状态，等待后端返回 session_id）
 * - 删除会话（调用后端 API）
 * - 会话切换
 */
export function useConversations() {
  const [conversations, setConversations] = useState([]);
  const [currentId, setCurrentId] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // 加载会话列表
  const loadConversations = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchSessions(50, 0);
      setConversations(data.sessions || []);
    } catch (e) {
      console.error('Failed to load conversations:', e);
      setError(e.message);
      // 加载失败时保持空列表，不影响使用
      setConversations([]);
    } finally {
      setLoading(false);
    }
  }, []);

  // 组件挂载时加载会话列表
  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  // 创建新会话（清空当前状态）
  // 实际的 session_id 由后端在 analyze/chat 时返回
  const createConversation = useCallback(() => {
    setCurrentId(null);
    return null;
  }, []);

  // 选择会话
  const selectConversation = useCallback((id) => {
    setCurrentId(id);
  }, []);

  // 删除会话
  const deleteConversation = useCallback(async (id) => {
    try {
      await apiDeleteSession(id);
      setConversations(prev => prev.filter(c => c.session_id !== id));
      if (currentId === id) {
        setCurrentId(null);
      }
    } catch (e) {
      console.error('Failed to delete conversation:', e);
      setError(e.message);
    }
  }, [currentId]);

  // 添加新会话到列表（当后端返回 session_id 时调用）
  const addConversation = useCallback((session) => {
    setConversations(prev => {
      // 检查是否已存在
      if (prev.some(c => c.session_id === session.session_id)) {
        // 更新已存在的会话
        return prev.map(c =>
          c.session_id === session.session_id
            ? { ...c, ...session }
            : c
        );
      }
      // 添加新会话到列表顶部
      return [session, ...prev];
    });
    setCurrentId(session.session_id);
  }, []);

  // 更新会话（如标题）
  const updateConversation = useCallback((id, updates) => {
    setConversations(prev => prev.map(c =>
      c.session_id === id ? { ...c, ...updates } : c
    ));
  }, []);

  // 过滤后的会话列表（客户端搜索）- 使用 useMemo 缓存
  const filteredConversations = useMemo(() => {
    if (!searchQuery) return conversations;
    const query = searchQuery.toLowerCase();
    return conversations.filter(c =>
      c.title?.toLowerCase().includes(query) ||
      c.first_message?.toLowerCase().includes(query)
    );
  }, [conversations, searchQuery]);

  return {
    conversations: filteredConversations,
    currentId,
    searchQuery,
    setSearchQuery,
    loading,
    error,
    loadConversations,
    createConversation,
    selectConversation,
    deleteConversation,
    addConversation,
    updateConversation,
    setCurrentId,
  };
}
