/**
 * 认证状态 Hook 和 AuthProvider
 *
 * 提供:
 * - useAuth: 获取认证状态和方法
 * - AuthProvider: 认证状态上下文提供者
 * - ProtectedRoute: 保护路由组件
 */
import React, { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  login as apiLogin,
  register as apiRegister,
  logout as apiLogout,
  getCurrentUser,
  getAccessToken,
  getRefreshToken,
  getCachedUser,
  clearTokens,
  refreshTokens,
  getOAuthProviders,
} from '../services/auth';

// ========== Context ==========

const AuthContext = createContext(null);

// ========== Provider ==========

/**
 * AuthProvider - 认证状态提供者
 */
export function AuthProvider({ children }) {
  // 状态
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [oauthProviders, setOauthProviders] = useState({ github: false, google: false });

  // 初始化：检查本地存储的 Token
  useEffect(() => {
    const initAuth = async () => {
      const token = getAccessToken();

      if (!token) {
        setLoading(false);
        return;
      }

      // 先使用缓存的用户信息
      const cachedUser = getCachedUser();
      if (cachedUser) {
        setUser(cachedUser);
      }

      // 然后验证 Token 并获取最新用户信息
      try {
        const userData = await getCurrentUser();
        setUser(userData);
      } catch (e) {
        // Token 无效，尝试刷新
        if (getRefreshToken()) {
          try {
            const refreshData = await refreshTokens();
            setUser(refreshData.user);
          } catch {
            // 刷新失败，清除 Token
            clearTokens();
            setUser(null);
          }
        } else {
          clearTokens();
          setUser(null);
        }
      } finally {
        setLoading(false);
      }
    };

    initAuth();
  }, []);

  // 获取 OAuth 提供商状态
  useEffect(() => {
    const fetchProviders = async () => {
      try {
        const providers = await getOAuthProviders();
        setOauthProviders(providers);
      } catch (e) {
        console.warn('Failed to fetch OAuth providers:', e);
      }
    };

    fetchProviders();
  }, []);

  // 登录
  const login = useCallback(async (email, password) => {
    setError(null);
    setLoading(true);

    try {
      const data = await apiLogin(email, password);
      setUser(data.user);
      return data;
    } catch (e) {
      setError(e.message);
      throw e;
    } finally {
      setLoading(false);
    }
  }, []);

  // 注册
  const register = useCallback(async (email, password, displayName = null) => {
    setError(null);
    setLoading(true);

    try {
      const data = await apiRegister(email, password, displayName);
      setUser(data.user);
      return data;
    } catch (e) {
      setError(e.message);
      throw e;
    } finally {
      setLoading(false);
    }
  }, []);

  // 登出
  const logout = useCallback(async () => {
    setLoading(true);

    try {
      await apiLogout();
    } finally {
      setUser(null);
      setLoading(false);
    }
  }, []);

  // 更新用户信息
  const updateUser = useCallback((userData) => {
    setUser(prev => ({ ...prev, ...userData }));
  }, []);

  // 清除错误
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  // 计算属性
  const isAuthenticated = useMemo(() => !!user, [user]);
  const isEmailVerified = useMemo(() => user?.email_verified || false, [user]);

  // Context 值
  const value = useMemo(() => ({
    // 状态
    user,
    loading,
    error,
    isAuthenticated,
    isEmailVerified,
    oauthProviders,

    // 方法
    login,
    register,
    logout,
    updateUser,
    clearError,
  }), [
    user,
    loading,
    error,
    isAuthenticated,
    isEmailVerified,
    oauthProviders,
    login,
    register,
    logout,
    updateUser,
    clearError,
  ]);

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

// ========== Hook ==========

/**
 * useAuth - 获取认证状态和方法
 */
export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }

  return context;
}

// ========== 保护路由 ==========

/**
 * ProtectedRoute - 保护路由组件
 *
 * 未登录用户重定向到登录页
 */
export function ProtectedRoute({ children, requireVerified = false }) {
  const { isAuthenticated, isEmailVerified, loading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    if (!loading) {
      if (!isAuthenticated) {
        // 保存当前路径，登录后跳转回来
        navigate('/auth/login', {
          replace: true,
          state: { from: location.pathname },
        });
      } else if (requireVerified && !isEmailVerified) {
        // 需要邮箱验证但未验证
        navigate('/auth/verify-email', { replace: true });
      }
    }
  }, [isAuthenticated, isEmailVerified, loading, navigate, location.pathname, requireVerified]);

  // 加载中显示空白或加载指示器
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-background-dark">
        <div className="animate-spin rounded-full h-8 w-8 border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  // 未登录返回 null（useEffect 会处理重定向）
  if (!isAuthenticated) {
    return null;
  }

  // 需要验证但未验证
  if (requireVerified && !isEmailVerified) {
    return null;
  }

  return children;
}

/**
 * PublicOnlyRoute - 仅未登录用户可访问
 *
 * 已登录用户重定向到首页
 */
export function PublicOnlyRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    if (!loading && isAuthenticated) {
      // 如果有保存的来源路径，跳转回去
      const from = location.state?.from || '/';
      navigate(from, { replace: true });
    }
  }, [isAuthenticated, loading, navigate, location.state]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-background-dark">
        <div className="animate-spin rounded-full h-8 w-8 border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  if (isAuthenticated) {
    return null;
  }

  return children;
}

export default useAuth;
