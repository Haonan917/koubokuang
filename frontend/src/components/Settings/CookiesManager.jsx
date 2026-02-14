import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { Cookie, Plus, Pencil, Trash2, Save, X, Loader2, AlertCircle } from 'lucide-react';
import { fetchCookiesList, fetchCookiesDetail, saveCookies, deleteCookies } from '../../services/api';
import Popconfirm from '../ui/Popconfirm';
import Select from '../ui/Select';

/**
 * 平台配置 - 使用 Material Symbols 图标
 */
const PLATFORMS = [
  { key: 'xhs', icon: 'book_2', iconColor: 'text-red-400', subtitle: 'Xiaohongshu', logo: '/assets/logos/xhs.png' },
  { key: 'dy', icon: 'music_note', iconColor: 'text-pink-400', subtitle: 'Douyin', logo: '/assets/logos/dy.png' },
  { key: 'bili', icon: 'tv', iconColor: 'text-cyan-400', subtitle: 'Bilibili', logo: '/assets/logos/bili.png' },
  { key: 'ks', icon: 'bolt', iconColor: 'text-orange-400', subtitle: 'Kuaishou', logo: '/assets/logos/ks.png' },
];

/**
 * 状态配置 - 使用指示点样式
 */
const STATUS_CONFIG = {
  valid: { dot: 'bg-emerald-400', text: 'text-emerald-400', glow: 'shadow-[0_0_8px_rgba(52,211,153,0.5)]' },
  expired: { dot: 'bg-amber-400', text: 'text-amber-400', glow: 'shadow-[0_0_8px_rgba(251,191,36,0.5)]' },
  disabled: { dot: 'bg-slate-500', text: 'text-slate-400', glow: '' },
};

/**
 * CookiesManager - Cookies 管理面板
 *
 * 列表展示所有平台 cookies，支持新增、编辑、删除
 */
function CookiesManager() {
  const { t } = useTranslation();

  // 列表数据
  const [cookies, setCookies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // 编辑状态: null=关闭表单, 'new'=新增, 'xhs'/'dy'/...=编辑
  const [editing, setEditing] = useState(null);
  const [formData, setFormData] = useState({ platform: '', cookies: '', remark: '' });
  const [saving, setSaving] = useState(false);
  const [fetchingDetail, setFetchingDetail] = useState(false);
  const [formError, setFormError] = useState(null);

  // 获取列表
  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchCookiesList();
      setCookies(data || []);
    } catch (err) {
      setError(err.message || t('errors.fetchFailed'));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // 打开新增表单
  const handleAddNew = () => {
    // 找出未配置的平台
    const configuredPlatforms = cookies.map(c => c.platform);
    const availablePlatforms = PLATFORMS.filter(p => !configuredPlatforms.includes(p.key));

    if (availablePlatforms.length === 0) {
      setFormError(t('settings.allPlatformsConfigured'));
      return;
    }

    setFormData({ platform: availablePlatforms[0].key, cookies: '', remark: '' });
    setEditing('new');
    setFormError(null);
  };

  // 打开编辑表单（异步获取 cookies 详情）
  const handleEdit = async (item) => {
    setFormError(null);
    setEditing(item.platform);
    setFetchingDetail(true);
    // 先设置平台和备注，cookies 稍后填充
    setFormData({
      platform: item.platform,
      cookies: '',
      remark: item.remark || '',
    });

    try {
      const detail = await fetchCookiesDetail(item.platform);
      setFormData({
        platform: detail.platform,
        cookies: detail.cookies || '',
        remark: detail.remark || '',
      });
    } catch (err) {
      setFormError(t('errors.fetchFailed') + ': ' + err.message);
    } finally {
      setFetchingDetail(false);
    }
  };

  // 关闭表单
  const handleCancel = () => {
    setEditing(null);
    setFormData({ platform: '', cookies: '', remark: '' });
    setFormError(null);
  };

  // 保存
  const handleSave = async () => {
    if (!formData.platform) {
      setFormError(t('settings.platformRequired'));
      return;
    }
    if (!formData.cookies.trim()) {
      setFormError(t('settings.cookiesRequired'));
      return;
    }

    setSaving(true);
    setFormError(null);
    try {
      await saveCookies(formData.platform, formData.cookies, formData.remark);
      await fetchData();
      handleCancel();
    } catch (err) {
      setFormError(err.message || t('errors.unknown'));
    } finally {
      setSaving(false);
    }
  };

  // 删除
  const handleDelete = async (platform) => {
    try {
      await deleteCookies(platform);
      await fetchData();
    } catch (err) {
      setError(err.message || t('errors.unknown'));
    }
  };

  // 获取平台显示信息
  const getPlatformInfo = (key) => {
    const platform = PLATFORMS.find(p => p.key === key);
    return {
      icon: platform?.icon || 'description',
      iconColor: platform?.iconColor || 'text-text-muted',
      logo: platform?.logo || null,
      name: t(`platforms.${key}`) || key,
    };
  };

  // 格式化日期
  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  // 获取可选平台（新增时过滤已配置的）
  const getAvailablePlatforms = () => {
    if (editing === 'new') {
      const configuredPlatforms = cookies.map(c => c.platform);
      return PLATFORMS.filter(p => !configuredPlatforms.includes(p.key));
    }
    return PLATFORMS;
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold text-text-primary flex items-center gap-2">
            <Cookie size={20} className="text-primary" />
            {t('settings.cookies')}
          </h3>
          <p className="text-sm text-text-muted mt-1">{t('settings.cookiesDesc')}</p>
        </div>
        {!editing && (
          <button
            onClick={handleAddNew}
            className="flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary-hover text-white rounded-lg transition-colors text-sm font-medium"
          >
            <Plus size={16} />
            {t('settings.addCookies')}
          </button>
        )}
      </div>

      {/* Error Alert */}
      {error && (
        <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg flex items-center gap-2 text-red-400 text-sm">
          <AlertCircle size={16} />
          {error}
        </div>
      )}

      {/* Loading */}
      {loading && !editing && (
        <div className="flex-1 flex items-center justify-center">
          <Loader2 size={24} className="animate-spin text-primary" />
        </div>
      )}

      {/* 编辑表单 */}
      {editing && (
        <div className="mb-6 p-4 bg-card-bg border border-slate-border rounded-xl">
          <h4 className="text-sm font-medium text-text-primary mb-4">
            {editing === 'new' ? t('settings.addCookies') : t('settings.editCookies')}
          </h4>

          {/* Platform Select */}
          <div className="mb-4">
            <label className="block text-sm text-text-secondary mb-2">{t('settings.platform')}</label>
            <Select
              value={formData.platform}
              onChange={(val) => setFormData({ ...formData, platform: val })}
              disabled={editing !== 'new'}
              options={getAvailablePlatforms().map((p) => ({
                value: p.key,
                label: t(`platforms.${p.key}`),
                subtitle: p.subtitle,
                icon: p.icon,
                iconColor: p.iconColor,
                logo: p.logo,
              }))}
              placeholder={t('settings.platform')}
            />
          </div>

          {/* Cookies Textarea */}
          <div className="mb-4">
            <label className="block text-sm text-text-secondary mb-2">{t('settings.cookiesValue')}</label>
            <div className="relative">
              <textarea
                value={formData.cookies}
                onChange={(e) => setFormData({ ...formData, cookies: e.target.value })}
                placeholder={fetchingDetail ? t('settings.loadingCookies') : t('settings.cookiesPlaceholder')}
                rows={6}
                disabled={fetchingDetail}
                className="w-full px-3 py-2 bg-sidebar-dark border border-slate-border rounded-lg text-text-primary text-sm font-mono focus:outline-none focus:border-primary resize-none disabled:opacity-50"
              />
              {fetchingDetail && (
                <div className="absolute inset-0 flex items-center justify-center bg-sidebar-dark/50 rounded-lg">
                  <Loader2 size={20} className="animate-spin text-primary" />
                </div>
              )}
            </div>
          </div>

          {/* Remark Input */}
          <div className="mb-4">
            <label className="block text-sm text-text-secondary mb-2">{t('settings.remark')}</label>
            <input
              type="text"
              value={formData.remark}
              onChange={(e) => setFormData({ ...formData, remark: e.target.value })}
              placeholder={t('settings.remarkPlaceholder')}
              className="w-full px-3 py-2 bg-sidebar-dark border border-slate-border rounded-lg text-text-primary text-sm focus:outline-none focus:border-primary"
            />
          </div>

          {/* Form Error */}
          {formError && (
            <div className="mb-4 p-2 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
              {formError}
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center justify-end gap-3">
            <button
              onClick={handleCancel}
              className="px-4 py-2 text-text-secondary hover:text-text-primary transition-colors text-sm"
            >
              {t('settings.cancel')}
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary-hover text-white rounded-lg transition-colors text-sm font-medium disabled:opacity-50"
            >
              {saving ? (
                <Loader2 size={16} className="animate-spin" />
              ) : (
                <Save size={16} />
              )}
              {t('settings.save')}
            </button>
          </div>
        </div>
      )}

      {/* Cookies 列表 */}
      {!loading && !editing && (
        <div className="flex-1 overflow-y-auto custom-scrollbar">
          {cookies.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-text-muted">
              <Cookie size={48} className="mb-4 opacity-50" />
              <p className="text-sm">{t('settings.noCookies')}</p>
            </div>
          ) : (
            <div className="space-y-2">
              {cookies.map((item) => {
                const { icon, iconColor, logo, name } = getPlatformInfo(item.platform);
                const statusKey = item.status || 'valid';
                const status = STATUS_CONFIG[statusKey] || STATUS_CONFIG.valid;
                return (
                  <div
                    key={item.platform}
                    className="group relative p-4 bg-gradient-to-r from-card-bg to-card-bg/80 border border-slate-border/60 rounded-xl hover:border-primary/40 hover:bg-card-bg/90 transition-all duration-200"
                  >
                    <div className="flex items-center gap-4">
                      {/* Platform Icon */}
                      <div className="relative w-10 h-10 flex items-center justify-center rounded-xl bg-slate-800/50 border border-slate-700/50">
                        {logo ? (
                          <img
                            src={logo}
                            alt={name}
                            className="w-6 h-6 object-contain"
                            onError={(e) => {
                              e.target.style.display = 'none';
                              const fallback = e.target.nextSibling;
                              if (fallback) fallback.style.display = 'inline';
                            }}
                          />
                        ) : null}
                        <span
                          className={`material-symbols-outlined text-xl ${iconColor}`}
                          style={{ display: logo ? 'none' : 'inline' }}
                        >
                          {icon}
                        </span>
                      </div>

                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2.5">
                          <h4 className="text-sm font-semibold text-text-primary tracking-wide">{name}</h4>
                          {/* Status Indicator */}
                          <div className="flex items-center gap-1.5">
                            <span className={`w-1.5 h-1.5 rounded-full ${status.dot} ${status.glow}`} />
                            <span className={`text-[11px] font-medium ${status.text}`}>
                              {t(`settings.status${statusKey.charAt(0).toUpperCase() + statusKey.slice(1)}`)}
                            </span>
                          </div>
                        </div>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="text-[11px] text-text-muted/70 font-mono">
                            {formatDate(item.updated_at)}
                          </span>
                          {item.remark && (
                            <>
                              <span className="text-text-muted/30">·</span>
                              <span className="text-[11px] text-text-muted/70 truncate max-w-[200px]">
                                {item.remark}
                              </span>
                            </>
                          )}
                        </div>
                      </div>

                      {/* Actions */}
                      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                        <button
                          onClick={() => handleEdit(item)}
                          className="p-2 text-text-muted/60 hover:text-primary hover:bg-primary/10 rounded-lg transition-all duration-150"
                          title={t('settings.edit')}
                        >
                          <Pencil size={15} />
                        </button>
                        <Popconfirm
                          title={t('settings.deleteConfirm')}
                          confirmText={t('sidebar.confirm')}
                          cancelText={t('sidebar.cancel')}
                          onConfirm={() => handleDelete(item.platform)}
                          placement="left"
                        >
                          <button
                            className="p-2 text-text-muted/60 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-all duration-150"
                            title={t('settings.delete')}
                          >
                            <Trash2 size={15} />
                          </button>
                        </Popconfirm>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default CookiesManager;
