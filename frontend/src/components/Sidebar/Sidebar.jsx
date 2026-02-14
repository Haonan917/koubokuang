import React, { memo, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { Settings, LogOut, User } from 'lucide-react';
import Popconfirm from '../ui/Popconfirm';
import { SettingsDialog } from '../Settings';
import { useAuth } from '../../hooks/useAuth';

/**
 * Sidebar - Remix AI Studio 深色主题侧边栏
 *
 * Premium 风格的导航侧边栏
 * 包含品牌 Logo、新会话按钮和按日期分组的历史列表
 */
function Sidebar({
  isOpen,
  onClose,
  conversations,
  currentId,
  onSelect,
  onNew,
  onDelete,
}) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user, isAuthenticated, logout } = useAuth();
  const [settingsOpen, setSettingsOpen] = useState(false);

  const handleLogout = async () => {
    await logout();
    navigate('/');
  };

  const handleLogin = () => {
    navigate('/auth/login');
  };

  // 按日期分组会话
  const groupedConversations = useMemo(() => {
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);

    const groups = {
      today: [],
      yesterday: [],
      older: [],
    };

    conversations.forEach(conv => {
      const convDate = new Date(conv.updated_at || conv.created_at);
      convDate.setHours(0, 0, 0, 0);

      if (convDate.getTime() === today.getTime()) {
        groups.today.push(conv);
      } else if (convDate.getTime() === yesterday.getTime()) {
        groups.yesterday.push(conv);
      } else {
        groups.older.push(conv);
      }
    });

    return groups;
  }, [conversations]);

  // 渲染会话项
  const renderConversationItem = (conv) => {
    const convId = conv.session_id || conv.id;
    const isActive = currentId === convId;

    return (
      <div key={convId} className="group relative">
        <button
          onClick={() => onSelect(convId)}
          className={`
            w-full flex items-start gap-2.5 pl-4 pr-10 py-2.5 rounded-xl text-left
            transition-all duration-200
            ${isActive
              ? 'bg-primary/10 border border-primary/20'
              : 'hover:bg-white/5 border border-transparent'
            }
          `}
        >
          {/* Icon - 与标题对齐 */}
          <span className={`material-symbols-outlined text-[18px] mt-0.5 ${isActive ? 'text-primary sidebar-item-icon' : 'text-text-muted/60'}`}>
            {isActive ? 'chat_bubble' : 'chat_bubble_outline'}
          </span>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <p className={`text-[13px] leading-tight truncate ${isActive ? 'font-semibold text-text-primary' : 'font-medium text-text-secondary'}`}>
              {conv.title || t('sidebar.newAnalysis')}
            </p>
            <p className={`text-[11px] mt-1 ${isActive ? 'text-primary/70 sidebar-item-time' : 'text-text-muted'}`}>
              {getRelativeTime(conv.updated_at || conv.created_at, t)}
              {conv.type && ` • ${conv.type}`}
            </p>
          </div>
        </button>

        {/* Delete button on hover with Popconfirm */}
        <div className="absolute right-2 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity">
          <Popconfirm
            title={t('sidebar.deleteConfirm')}
            confirmText={t('sidebar.confirm')}
            cancelText={t('sidebar.cancel')}
            onConfirm={() => onDelete(convId)}
            placement="right"
          >
            <button
              type="button"
              aria-label={`Delete ${conv.title || t('sidebar.newAnalysis')}`}
              className="p-1.5 text-text-muted hover:text-accent-pink hover:bg-accent-pink/10 rounded-lg transition-all"
            >
              <span className="material-symbols-outlined text-sm">delete</span>
            </button>
          </Popconfirm>
        </div>
      </div>
    );
  };

  return (
    <>
      {/* Mobile Overlay */}
      {isOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-black/60 backdrop-blur-sm z-40 transition-opacity"
          onClick={onClose}
        />
      )}

      {/* Sidebar Container - Fixed 300px */}
      <aside
        className={`
          fixed lg:static inset-y-0 left-0 z-50
          w-[300px] flex-shrink-0 bg-bg-primary border-r border-border-default
          flex flex-col h-full
          transition-transform duration-300 ease-in-out
          ${isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
        `}
      >
        {/* Inner padding container */}
        <div className="p-6 flex flex-col gap-8 h-full">
          {/* Header - Logo */}
          <div className="flex items-center gap-3">
            {/* Logo icon */}
            <img src="/assets/logo_width.png" alt="Logo" className="h-10 object-contain" />
            {/* Brand text */}
            <div className="flex flex-col">
              <h1 className="font-display font-bold text-lg leading-tight text-text-primary">
                {t('app.name')}
              </h1>
              <p className="text-[10px] text-text-muted font-bold uppercase tracking-widest">
                {t('app.tagline')}
              </p>
            </div>
          </div>

          {/* New Session Button */}
          <button
            type="button"
            onClick={onNew}
            className="btn-new-session"
          >
            <span className="material-symbols-outlined text-xl">add_circle</span>
            {t('sidebar.newSession')}
          </button>

          {/* Conversation History */}
          <div className="flex-1 overflow-y-auto custom-scrollbar flex flex-col gap-6">
            {/* Today section */}
            {groupedConversations.today.length > 0 && (
              <div>
                <p className="sidebar-section-title">{t('sidebar.today')}</p>
                <div className="flex flex-col gap-2">
                  {groupedConversations.today.map(renderConversationItem)}
                </div>
              </div>
            )}

            {/* Yesterday section */}
            {groupedConversations.yesterday.length > 0 && (
              <div>
                <p className="sidebar-section-title">{t('sidebar.yesterday')}</p>
                <div className="flex flex-col gap-2">
                  {groupedConversations.yesterday.map(renderConversationItem)}
                </div>
              </div>
            )}

            {/* Older section */}
            {groupedConversations.older.length > 0 && (
              <div>
                <p className="sidebar-section-title">{t('sidebar.earlier')}</p>
                <div className="flex flex-col gap-2">
                  {groupedConversations.older.map(renderConversationItem)}
                </div>
              </div>
            )}

            {/* Empty state */}
            {conversations.length === 0 && (
              <div className="text-center py-8">
                <p className="text-sm text-text-muted">{t('sidebar.noSessions')}</p>
                <p className="text-xs text-text-muted mt-1">{t('sidebar.startHint')}</p>
              </div>
            )}
          </div>

          {/* Bottom Section - User Info & Settings */}
          <div className="pt-4 border-t border-border-default mt-auto space-y-2">
            {/* User Info / Login Button */}
            {isAuthenticated ? (
              <div className="flex items-center gap-3 px-4 py-3">
                {/* Avatar */}
                {user?.avatar_url ? (
                  <img
                    src={user.avatar_url}
                    alt={user.display_name || user.email}
                    className="w-8 h-8 rounded-lg object-cover"
                  />
                ) : (
                  <div className="w-8 h-8 bg-primary/10 rounded-lg flex items-center justify-center">
                    <User size={18} className="text-primary" />
                  </div>
                )}
                {/* Name & Email */}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-text-primary truncate">
                    {user?.display_name || user?.email?.split('@')[0]}
                  </p>
                  <p className="text-xs text-text-muted truncate">{user?.email}</p>
                </div>
                {/* Logout Button */}
                <button
                  type="button"
                  onClick={handleLogout}
                  className="p-2 text-text-muted hover:text-red-400 hover:bg-red-400/10 rounded-lg transition-colors"
                  title={t('auth.logout')}
                >
                  <LogOut size={16} />
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={handleLogin}
                className="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-left transition-all duration-200 hover:bg-white/5 border border-transparent group"
              >
                <span className="w-8 h-8 bg-primary/10 rounded-lg flex items-center justify-center transition-colors">
                  <User size={18} className="text-primary" />
                </span>
                <span className="text-sm font-medium text-text-secondary group-hover:text-text-primary transition-colors">
                  {t('auth.login')}
                </span>
              </button>
            )}

            {/* Settings Button */}
            <button
              type="button"
              onClick={() => setSettingsOpen(true)}
              className="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-left transition-all duration-200 hover:bg-white/5 border border-transparent group"
            >
              <span className="w-8 h-8 bg-primary/10 rounded-lg flex items-center justify-center transition-colors">
                <Settings size={18} className="text-primary transition-colors" />
              </span>
              <span className="text-sm font-medium text-text-secondary group-hover:text-text-primary transition-colors">
                {t('settings.title')}
              </span>
            </button>
          </div>
        </div>
      </aside>

      {/* Settings Dialog */}
      <SettingsDialog isOpen={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </>
  );
}

/**
 * 获取相对时间描述
 * @param {string} dateString - 日期字符串
 * @param {Function} t - i18n 翻译函数
 */
function getRelativeTime(dateString, t) {
  if (!dateString) return '';

  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return t('time.justNow');
  if (diffMins < 60) return t('time.minutesAgo', { count: diffMins });
  if (diffHours < 24) return t('time.hoursAgo', { count: diffHours });
  if (diffDays === 1) return t('time.yesterday');
  if (diffDays < 7) return t('time.daysAgo', { count: diffDays });

  return date.toLocaleDateString();
}

export default memo(Sidebar);
