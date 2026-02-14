import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Palette, Plus, Pencil, Trash2, Save, X, Loader2, AlertCircle,
  CheckCircle, GripVertical, Eye, EyeOff, Lock, ChevronDown, ChevronUp
} from 'lucide-react';
import {
  fetchInsightModeList,
  fetchInsightMode,
  createInsightMode,
  updateInsightMode,
  deleteInsightMode,
  toggleInsightMode,
  reorderInsightModes,
} from '../../services/api';
import { invalidateModesCache } from '../../constants/modes';
import Popconfirm from '../ui/Popconfirm';
import Select from '../ui/Select';

/**
 * 颜色配置
 */
const COLORS = [
  { key: 'cyan', label: 'Cyan', class: 'bg-accent-cyan', preview: 'bg-accent-cyan/20 border-accent-cyan/30' },
  { key: 'orange', label: 'Orange', class: 'bg-accent-orange', preview: 'bg-accent-orange/20 border-accent-orange/30' },
  { key: 'pink', label: 'Pink', class: 'bg-accent-pink', preview: 'bg-accent-pink/20 border-accent-pink/30' },
  { key: 'purple', label: 'Purple', class: 'bg-accent-purple', preview: 'bg-accent-purple/20 border-accent-purple/30' },
];

/**
 * 常用图标列表
 */
const ICONS = [
  'format_list_bulleted', 'layers', 'article', 'palette',
  'smart_toy', 'psychology', 'auto_awesome', 'lightbulb',
  'edit_note', 'code', 'insights', 'analytics',
];

/**
 * 初始表单数据
 */
const INITIAL_FORM = {
  mode_key: '',
  label_zh: '',
  label_en: '',
  description_zh: '',
  description_en: '',
  prefill_zh: '',
  prefill_en: '',
  icon: 'smart_toy',
  color: 'cyan',
  keywords_zh: '',
  keywords_en: '',
  system_prompt: '',
};

/**
 * InsightModeManager - 分析模式管理面板
 *
 * 支持:
 * - 模式列表展示
 * - 新增/编辑模式
 * - 删除模式（系统模式不可删）
 * - 启用/禁用切换
 * - 拖拽排序
 */
function InsightModeManager() {
  const { t, i18n } = useTranslation();
  const isZh = i18n.language === 'zh';

  // 列表数据
  const [modes, setModes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // 编辑状态: null=关闭表单, 'new'=新增, mode_key=编辑
  const [editing, setEditing] = useState(null);
  const [formData, setFormData] = useState(INITIAL_FORM);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState(null);

  // UI 状态
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [draggingKey, setDraggingKey] = useState(null);

  // 获取列表
  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchInsightModeList(false);
      setModes(data.items || []);
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
    setFormData(INITIAL_FORM);
    setEditing('new');
    setFormError(null);
    setShowAdvanced(false);
  };

  // 打开编辑表单
  const handleEdit = async (item) => {
    try {
      // 获取完整详情（包含 system_prompt）
      const detail = await fetchInsightMode(item.mode_key);
      setFormData({
        mode_key: detail.mode_key,
        label_zh: detail.label_zh || '',
        label_en: detail.label_en || '',
        description_zh: detail.description_zh || '',
        description_en: detail.description_en || '',
        prefill_zh: detail.prefill_zh || '',
        prefill_en: detail.prefill_en || '',
        icon: detail.icon || 'smart_toy',
        color: detail.color || 'cyan',
        keywords_zh: detail.keywords_zh || '',
        keywords_en: detail.keywords_en || '',
        system_prompt: detail.system_prompt || '',
      });
      setEditing(item.mode_key);
      setFormError(null);
      setShowAdvanced(false);
    } catch (err) {
      setError(err.message);
    }
  };

  // 关闭表单
  const handleCancel = () => {
    setEditing(null);
    setFormData(INITIAL_FORM);
    setFormError(null);
    setShowAdvanced(false);
  };

  // 保存
  const handleSave = async () => {
    // 验证必填字段
    if (!formData.mode_key.trim()) {
      setFormError(t('insightModes.modeKeyRequired'));
      return;
    }
    if (!formData.label_zh.trim() || !formData.label_en.trim()) {
      setFormError(t('insightModes.labelRequired'));
      return;
    }
    if (!formData.system_prompt.trim()) {
      setFormError(t('insightModes.promptRequired'));
      return;
    }

    setSaving(true);
    setFormError(null);
    try {
      if (editing === 'new') {
        await createInsightMode(formData);
      } else {
        const updateData = { ...formData };
        delete updateData.mode_key; // mode_key 在 URL 中
        await updateInsightMode(editing, updateData);
      }
      invalidateModesCache(); // 清除模式选择器缓存
      await fetchData();
      handleCancel();
    } catch (err) {
      setFormError(err.message || t('errors.unknown'));
    } finally {
      setSaving(false);
    }
  };

  // 删除
  const handleDelete = async (modeKey) => {
    try {
      await deleteInsightMode(modeKey);
      invalidateModesCache(); // 清除模式选择器缓存
      await fetchData();
    } catch (err) {
      setError(err.message || t('errors.unknown'));
    }
  };

  // 切换启用状态
  const handleToggle = async (modeKey) => {
    try {
      await toggleInsightMode(modeKey);
      invalidateModesCache(); // 清除模式选择器缓存
      await fetchData();
    } catch (err) {
      setError(err.message || t('errors.unknown'));
    }
  };

  // 拖拽排序
  const handleDragStart = (e, modeKey) => {
    setDraggingKey(modeKey);
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  };

  const handleDrop = async (e, targetKey) => {
    e.preventDefault();
    if (!draggingKey || draggingKey === targetKey) {
      setDraggingKey(null);
      return;
    }

    // 重新排序
    const newModes = [...modes];
    const dragIndex = newModes.findIndex(m => m.mode_key === draggingKey);
    const targetIndex = newModes.findIndex(m => m.mode_key === targetKey);

    if (dragIndex === -1 || targetIndex === -1) {
      setDraggingKey(null);
      return;
    }

    const [removed] = newModes.splice(dragIndex, 1);
    newModes.splice(targetIndex, 0, removed);

    setModes(newModes);
    setDraggingKey(null);

    // 保存新顺序
    try {
      await reorderInsightModes(newModes.map(m => m.mode_key));
      invalidateModesCache(); // 清除模式选择器缓存
    } catch (err) {
      setError(err.message);
      await fetchData(); // 恢复原顺序
    }
  };

  const handleDragEnd = () => {
    setDraggingKey(null);
  };

  // 获取颜色样式
  const getColorClass = (colorKey) => {
    const color = COLORS.find(c => c.key === colorKey);
    return color?.preview || 'bg-gray-500/20 border-gray-500/30';
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold text-text-primary flex items-center gap-2">
            <Palette size={20} className="text-primary" />
            {t('insightModes.title')}
          </h3>
          <p className="text-sm text-text-muted mt-1">{t('insightModes.desc')}</p>
        </div>
        {!editing && (
          <button
            onClick={handleAddNew}
            className="flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary-hover text-white rounded-lg transition-colors text-sm font-medium"
          >
            <Plus size={16} />
            {t('insightModes.addMode')}
          </button>
        )}
      </div>

      {/* Error Alert */}
      {error && (
        <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg flex items-center gap-2 text-red-400 text-sm">
          <AlertCircle size={16} />
          {error}
          <button onClick={() => setError(null)} className="ml-auto">
            <X size={14} />
          </button>
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
        <div className="flex-1 p-5 bg-card-bg border border-slate-border rounded-xl overflow-y-auto">
          <h4 className="text-sm font-medium text-text-primary mb-4">
            {editing === 'new' ? t('insightModes.addMode') : t('insightModes.editMode')}
          </h4>

          {/* Mode Key (新增时才显示) */}
          {editing === 'new' && (
            <div className="mb-4">
              <label className="block text-sm text-text-secondary mb-2">{t('insightModes.modeKey')} *</label>
              <input
                type="text"
                value={formData.mode_key}
                onChange={(e) => setFormData({ ...formData, mode_key: e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, '') })}
                placeholder="e.g., summarize, analyze"
                className="w-full px-3 py-2 bg-sidebar-dark border border-slate-border rounded-lg text-text-primary text-sm font-mono focus:outline-none focus:border-primary"
              />
              <p className="text-xs text-text-muted mt-1">{t('insightModes.modeKeyHint')}</p>
            </div>
          )}

          {/* 名称 */}
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm text-text-secondary mb-2">{t('insightModes.labelZh')} *</label>
              <input
                type="text"
                value={formData.label_zh}
                onChange={(e) => setFormData({ ...formData, label_zh: e.target.value })}
                placeholder="中文名称"
                className="w-full px-3 py-2 bg-sidebar-dark border border-slate-border rounded-lg text-text-primary text-sm focus:outline-none focus:border-primary"
              />
            </div>
            <div>
              <label className="block text-sm text-text-secondary mb-2">{t('insightModes.labelEn')} *</label>
              <input
                type="text"
                value={formData.label_en}
                onChange={(e) => setFormData({ ...formData, label_en: e.target.value })}
                placeholder="English Name"
                className="w-full px-3 py-2 bg-sidebar-dark border border-slate-border rounded-lg text-text-primary text-sm focus:outline-none focus:border-primary"
              />
            </div>
          </div>

          {/* 描述 */}
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm text-text-secondary mb-2">{t('insightModes.descZh')}</label>
              <input
                type="text"
                value={formData.description_zh}
                onChange={(e) => setFormData({ ...formData, description_zh: e.target.value })}
                placeholder="中文描述"
                className="w-full px-3 py-2 bg-sidebar-dark border border-slate-border rounded-lg text-text-primary text-sm focus:outline-none focus:border-primary"
              />
            </div>
            <div>
              <label className="block text-sm text-text-secondary mb-2">{t('insightModes.descEn')}</label>
              <input
                type="text"
                value={formData.description_en}
                onChange={(e) => setFormData({ ...formData, description_en: e.target.value })}
                placeholder="English Description"
                className="w-full px-3 py-2 bg-sidebar-dark border border-slate-border rounded-lg text-text-primary text-sm focus:outline-none focus:border-primary"
              />
            </div>
          </div>

          {/* 图标和颜色 */}
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm text-text-secondary mb-2">{t('insightModes.icon')}</label>
              <div className="flex flex-wrap gap-2">
                {ICONS.map((icon) => (
                  <button
                    key={icon}
                    type="button"
                    onClick={() => setFormData({ ...formData, icon })}
                    className={`w-10 h-10 flex items-center justify-center rounded-lg border transition-colors ${
                      formData.icon === icon
                        ? 'bg-primary/20 border-primary text-primary'
                        : 'bg-sidebar-dark border-slate-border text-text-muted hover:text-text-primary hover:border-primary/50'
                    }`}
                  >
                    <span className="material-symbols-outlined text-xl">{icon}</span>
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="block text-sm text-text-secondary mb-2">{t('insightModes.color')}</label>
              <div className="flex gap-2">
                {COLORS.map((color) => (
                  <button
                    key={color.key}
                    type="button"
                    onClick={() => setFormData({ ...formData, color: color.key })}
                    className={`w-10 h-10 rounded-lg border-2 transition-all ${color.class} ${
                      formData.color === color.key
                        ? 'ring-2 ring-offset-2 ring-offset-card-bg ring-white/50'
                        : 'opacity-60 hover:opacity-100'
                    }`}
                    title={color.label}
                  />
                ))}
              </div>
            </div>
          </div>

          {/* System Prompt */}
          <div className="mb-4">
            <label className="block text-sm text-text-secondary mb-2">{t('insightModes.systemPrompt')} *</label>
            <textarea
              value={formData.system_prompt}
              onChange={(e) => setFormData({ ...formData, system_prompt: e.target.value })}
              placeholder={t('insightModes.promptPlaceholder')}
              rows={12}
              className="w-full px-3 py-3 bg-sidebar-dark border border-slate-border rounded-lg text-text-primary text-sm font-mono focus:outline-none focus:border-primary resize-y min-h-[200px]"
            />
          </div>

          {/* Advanced Settings Toggle */}
          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="flex items-center gap-2 text-sm text-text-secondary hover:text-text-primary mb-4"
          >
            {showAdvanced ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            {t('insightModes.advancedSettings')}
          </button>

          {/* Advanced Settings */}
          {showAdvanced && (
            <div className="space-y-4 p-4 bg-sidebar-dark rounded-lg border border-slate-border/50 mb-4">
              {/* 预填充 */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-text-secondary mb-2">{t('insightModes.prefillZh')}</label>
                  <input
                    type="text"
                    value={formData.prefill_zh}
                    onChange={(e) => setFormData({ ...formData, prefill_zh: e.target.value })}
                    placeholder="输入框预填充文本"
                    className="w-full px-3 py-2 bg-main-bg border border-slate-border rounded-lg text-text-primary text-sm focus:outline-none focus:border-primary"
                  />
                </div>
                <div>
                  <label className="block text-sm text-text-secondary mb-2">{t('insightModes.prefillEn')}</label>
                  <input
                    type="text"
                    value={formData.prefill_en}
                    onChange={(e) => setFormData({ ...formData, prefill_en: e.target.value })}
                    placeholder="Input prefill text"
                    className="w-full px-3 py-2 bg-main-bg border border-slate-border rounded-lg text-text-primary text-sm focus:outline-none focus:border-primary"
                  />
                </div>
              </div>

              {/* 关键词 */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-text-secondary mb-2">{t('insightModes.keywordsZh')}</label>
                  <input
                    type="text"
                    value={formData.keywords_zh}
                    onChange={(e) => setFormData({ ...formData, keywords_zh: e.target.value })}
                    placeholder="总结,提炼,要点"
                    className="w-full px-3 py-2 bg-main-bg border border-slate-border rounded-lg text-text-primary text-sm focus:outline-none focus:border-primary"
                  />
                  <p className="text-xs text-text-muted mt-1">{t('insightModes.keywordsHint')}</p>
                </div>
                <div>
                  <label className="block text-sm text-text-secondary mb-2">{t('insightModes.keywordsEn')}</label>
                  <input
                    type="text"
                    value={formData.keywords_en}
                    onChange={(e) => setFormData({ ...formData, keywords_en: e.target.value })}
                    placeholder="summarize,summary,extract"
                    className="w-full px-3 py-2 bg-main-bg border border-slate-border rounded-lg text-text-primary text-sm focus:outline-none focus:border-primary"
                  />
                </div>
              </div>
            </div>
          )}

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

      {/* Mode 列表 */}
      {!loading && !editing && (
        <div className="flex-1 overflow-y-auto custom-scrollbar">
          {modes.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-text-muted">
              <Palette size={48} className="mb-4 opacity-50" />
              <p className="text-sm">{t('insightModes.noModes')}</p>
            </div>
          ) : (
            <div className="space-y-3">
              {modes.map((item) => {
                const isDragging = draggingKey === item.mode_key;
                return (
                  <div
                    key={item.mode_key}
                    draggable
                    onDragStart={(e) => handleDragStart(e, item.mode_key)}
                    onDragOver={handleDragOver}
                    onDrop={(e) => handleDrop(e, item.mode_key)}
                    onDragEnd={handleDragEnd}
                    className={`p-4 bg-card-bg border rounded-xl transition-all ${
                      isDragging
                        ? 'opacity-50 border-primary'
                        : item.is_active
                        ? 'border-slate-border hover:border-primary/30'
                        : 'border-slate-border/50 opacity-60'
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      {/* Drag Handle */}
                      <div className="cursor-grab text-text-muted hover:text-text-secondary mt-1">
                        <GripVertical size={16} />
                      </div>

                      {/* Icon */}
                      <div className={`w-10 h-10 rounded-lg flex items-center justify-center border ${getColorClass(item.color)}`}>
                        <span className="material-symbols-outlined text-xl">{item.icon || 'smart_toy'}</span>
                      </div>

                      {/* Info */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <h4 className="text-sm font-medium text-text-primary">
                            {isZh ? item.label_zh : item.label_en}
                          </h4>
                          <code className="text-xs px-1.5 py-0.5 bg-sidebar-dark rounded text-text-muted">
                            {item.mode_key}
                          </code>
                          {item.is_system && (
                            <span className="flex items-center gap-1 text-xs text-text-muted" title={t('insightModes.systemMode')}>
                              <Lock size={12} />
                            </span>
                          )}
                          {!item.is_active && (
                            <span className="flex items-center gap-1 text-xs px-2 py-0.5 bg-gray-500/10 text-gray-400 rounded-full">
                              <EyeOff size={12} />
                              {t('insightModes.disabled')}
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-text-muted mt-0.5 truncate">
                          {isZh ? item.description_zh : item.description_en}
                        </p>
                      </div>

                      {/* Actions */}
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => handleToggle(item.mode_key)}
                          className={`p-2 rounded-lg transition-colors ${
                            item.is_active
                              ? 'text-green-400 hover:bg-green-500/10'
                              : 'text-text-muted hover:bg-white/5 hover:text-text-primary'
                          }`}
                          title={item.is_active ? t('insightModes.disable') : t('insightModes.enable')}
                        >
                          {item.is_active ? <Eye size={16} /> : <EyeOff size={16} />}
                        </button>
                        <button
                          onClick={() => handleEdit(item)}
                          className="p-2 text-text-muted hover:text-primary hover:bg-primary/10 rounded-lg transition-colors"
                          title={t('settings.edit')}
                        >
                          <Pencil size={16} />
                        </button>
                        {!item.is_system ? (
                          <Popconfirm
                            title={t('insightModes.deleteConfirm')}
                            confirmText={t('sidebar.confirm')}
                            cancelText={t('sidebar.cancel')}
                            onConfirm={() => handleDelete(item.mode_key)}
                            placement="left"
                          >
                            <button
                              className="p-2 text-text-muted hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                              title={t('settings.delete')}
                            >
                              <Trash2 size={16} />
                            </button>
                          </Popconfirm>
                        ) : (
                          <button
                            disabled
                            className="p-2 text-text-muted/30 cursor-not-allowed rounded-lg"
                            title={t('insightModes.cannotDelete')}
                          >
                            <Trash2 size={16} />
                          </button>
                        )}
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

export default InsightModeManager;
