import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Bot, Plus, Pencil, Trash2, Save, X, Loader2, AlertCircle,
  CheckCircle, Zap, ChevronDown, ChevronUp, Eye, EyeOff
} from 'lucide-react';
import {
  fetchLLMConfigList,
  createLLMConfig,
  updateLLMConfig,
  deleteLLMConfig,
  activateLLMConfig,
  fetchLLMTemplates,
} from '../../services/api';
import Popconfirm from '../ui/Popconfirm';
import Select from '../ui/Select';

/**
 * 提供商配置 - 使用 Material Symbols 图标
 */
const PROVIDERS = [
  { key: 'openai', label: 'OpenAI / 兼容 API', labelEn: 'OpenAI / Compatible', icon: 'smart_toy', iconColor: 'text-green-400', subtitle: 'Kimi, MiniMax, GPT', hint: 'Kimi, MiniMax, GPT 等', logo: '/assets/logos/openai.png' },
  { key: 'anthropic', label: 'Anthropic Claude', labelEn: 'Anthropic Claude', icon: 'psychology', iconColor: 'text-orange-400', subtitle: 'Claude Sonnet/Opus', hint: 'Claude Sonnet/Opus', logo: '/assets/logos/anthropic.png' },
  { key: 'deepseek', label: 'DeepSeek', labelEn: 'DeepSeek', icon: 'explore', iconColor: 'text-blue-400', subtitle: 'Chat & Reasoner', hint: 'DeepSeek Chat/Reasoner', logo: '/assets/logos/deepseek.png' },
  { key: 'ollama', label: 'Ollama 本地', labelEn: 'Ollama Local', icon: 'computer', iconColor: 'text-purple-400', subtitle: 'Qwen, Llama', hint: 'Qwen, Llama 等本地模型', logo: '/assets/logos/ollma.png' },
];

/**
 * 初始表单数据
 */
const INITIAL_FORM = {
  config_name: '',
  provider: 'openai',
  api_key: '',
  base_url: '',
  model_name: '',
  enable_thinking: false,
  thinking_budget_tokens: 4096,
  reasoning_effort: 'high',
  support_multimodal: false,
  description: '',
};

/**
 * LLMConfigManager - LLM 配置管理面板 (简化版)
 *
 * 核心字段: provider, api_key, base_url, model_name
 * 可选字段: enable_thinking, thinking_budget_tokens (Anthropic), reasoning_effort (OpenAI)
 */
function LLMConfigManager() {
  const { t, i18n } = useTranslation();
  const isZh = i18n.language === 'zh';

  // 列表数据
  const [configs, setConfigs] = useState([]);
  const [activeConfig, setActiveConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // 模板数据
  const [templates, setTemplates] = useState({});

  // 编辑状态: null=关闭表单, 'new'=新增, 'config_name'=编辑
  const [editing, setEditing] = useState(null);
  const [formData, setFormData] = useState(INITIAL_FORM);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState(null);

  // UI 状态
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [showApiKey, setShowApiKey] = useState(false);

  // 获取列表
  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchLLMConfigList();
      setConfigs(data.items || []);
      setActiveConfig(data.active_config);
    } catch (err) {
      setError(err.message || t('errors.fetchFailed'));
    } finally {
      setLoading(false);
    }
  }, [t]);

  // 获取模板
  const fetchTemplatesData = useCallback(async () => {
    try {
      const data = await fetchLLMTemplates();
      setTemplates(data.templates || {});
    } catch (err) {
      console.error('Failed to fetch templates:', err);
    }
  }, []);

  useEffect(() => {
    fetchData();
    fetchTemplatesData();
  }, [fetchData, fetchTemplatesData]);

  // 打开新增表单
  const handleAddNew = () => {
    setFormData(INITIAL_FORM);
    setEditing('new');
    setFormError(null);
    setShowAdvanced(false);
    setShowApiKey(false);
  };

  // 打开编辑表单
  const handleEdit = (item) => {
    setFormData({
      config_name: item.config_name,
      provider: item.provider,
      api_key: '', // 不回填 API Key
      base_url: item.base_url || '',
      model_name: item.model_name,
      enable_thinking: item.enable_thinking || false,
      thinking_budget_tokens: item.thinking_budget_tokens || 4096,
      reasoning_effort: item.reasoning_effort || 'high',
      support_multimodal: item.support_multimodal || false,
      description: item.description || '',
    });
    setEditing(item.config_name);
    setFormError(null);
    setShowAdvanced(item.enable_thinking || item.support_multimodal);
    setShowApiKey(false);
  };

  // 关闭表单
  const handleCancel = () => {
    setEditing(null);
    setFormData(INITIAL_FORM);
    setFormError(null);
    setShowAdvanced(false);
    setShowApiKey(false);
  };

  // 应用模板
  const handleApplyTemplate = (template) => {
    setFormData(prev => ({
      ...prev,
      base_url: template.base_url || '',
      model_name: template.model_name || '',
      description: template.description || '',
      enable_thinking: template.enable_thinking || false,
      thinking_budget_tokens: template.thinking_budget_tokens || 4096,
      reasoning_effort: template.reasoning_effort || 'high',
      support_multimodal: template.support_multimodal || false,
    }));
    if (template.enable_thinking || template.support_multimodal) {
      setShowAdvanced(true);
    }
  };

  // 保存
  const handleSave = async () => {
    if (!formData.config_name.trim()) {
      setFormError(t('llmConfig.configNameRequired'));
      return;
    }
    if (!formData.model_name.trim()) {
      setFormError(t('llmConfig.modelNameRequired'));
      return;
    }

    setSaving(true);
    setFormError(null);
    try {
      if (editing === 'new') {
        await createLLMConfig(formData);
      } else {
        // 如果 api_key 为空，不更新它
        const updateData = { ...formData };
        if (!updateData.api_key) {
          delete updateData.api_key;
        }
        delete updateData.config_name; // config_name 在 URL 中
        await updateLLMConfig(editing, updateData);
      }
      await fetchData();
      handleCancel();
    } catch (err) {
      setFormError(err.message || t('errors.unknown'));
    } finally {
      setSaving(false);
    }
  };

  // 删除
  const handleDelete = async (configName) => {
    try {
      await deleteLLMConfig(configName);
      await fetchData();
    } catch (err) {
      setError(err.message || t('errors.unknown'));
    }
  };

  // 激活
  const handleActivate = async (configName) => {
    try {
      await activateLLMConfig(configName);
      await fetchData();
    } catch (err) {
      setError(err.message || t('errors.unknown'));
    }
  };

  // 获取提供商显示信息
  const getProviderInfo = (key) => {
    const provider = PROVIDERS.find(p => p.key === key);
    return {
      icon: provider?.icon || 'smart_toy',
      iconColor: provider?.iconColor || 'text-text-muted',
      logo: provider?.logo || null,
      label: isZh ? (provider?.label || key) : (provider?.labelEn || key),
    };
  };

  // 格式化日期
  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  // 获取当前提供商的模板
  const currentTemplates = templates[formData.provider] || [];

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold text-text-primary flex items-center gap-2">
            <Bot size={20} className="text-primary" />
            {t('llmConfig.title')}
          </h3>
          <p className="text-sm text-text-muted mt-1">{t('llmConfig.desc')}</p>
        </div>
        {!editing && (
          <button
            onClick={handleAddNew}
            className="flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary-hover text-white rounded-lg transition-colors text-sm font-medium"
          >
            <Plus size={16} />
            {t('llmConfig.addConfig')}
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
            {editing === 'new' ? t('llmConfig.addConfig') : t('llmConfig.editConfig')}
          </h4>

          {/* Config Name (新增时才显示) */}
          {editing === 'new' && (
            <div className="mb-4">
              <label className="block text-sm text-text-secondary mb-2">{t('llmConfig.configName')} *</label>
              <input
                type="text"
                value={formData.config_name}
                onChange={(e) => setFormData({ ...formData, config_name: e.target.value })}
                placeholder={t('llmConfig.configNamePlaceholder')}
                className="w-full px-3 py-2 bg-sidebar-dark border border-slate-border rounded-lg text-text-primary text-sm focus:outline-none focus:border-primary"
              />
            </div>
          )}

          {/* Provider Select */}
          <div className="mb-4">
            <label className="block text-sm text-text-secondary mb-2">{t('llmConfig.provider')} *</label>
            <Select
              value={formData.provider}
              onChange={(val) => setFormData({ ...formData, provider: val, base_url: '', model_name: '' })}
              options={PROVIDERS.map((p) => ({
                value: p.key,
                label: isZh ? p.label : p.labelEn,
                subtitle: p.subtitle,
                icon: p.icon,
                iconColor: p.iconColor,
                logo: p.logo,
              }))}
              placeholder={t('llmConfig.provider')}
            />
          </div>

          {/* 模板选择 */}
          {currentTemplates.length > 0 && (
            <div className="mb-4">
              <label className="block text-sm text-text-secondary mb-2">{t('llmConfig.templates')}</label>
              <div className="flex flex-wrap gap-2">
                {currentTemplates.map((tpl, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => handleApplyTemplate(tpl)}
                    className="px-3 py-1.5 text-xs bg-primary/10 hover:bg-primary/20 text-primary border border-primary/20 rounded-lg transition-colors"
                  >
                    {tpl.name}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Base URL */}
          <div className="mb-4">
            <label className="block text-sm text-text-secondary mb-2">{t('llmConfig.baseUrl')}</label>
            <input
              type="text"
              value={formData.base_url}
              onChange={(e) => setFormData({ ...formData, base_url: e.target.value })}
              placeholder={t('llmConfig.baseUrlPlaceholder')}
              className="w-full px-3 py-2 bg-sidebar-dark border border-slate-border rounded-lg text-text-primary text-sm font-mono focus:outline-none focus:border-primary"
            />
          </div>

          {/* Model Name */}
          <div className="mb-4">
            <label className="block text-sm text-text-secondary mb-2">{t('llmConfig.modelName')} *</label>
            <input
              type="text"
              value={formData.model_name}
              onChange={(e) => setFormData({ ...formData, model_name: e.target.value })}
              placeholder={t('llmConfig.modelNamePlaceholder')}
              className="w-full px-3 py-2 bg-sidebar-dark border border-slate-border rounded-lg text-text-primary text-sm font-mono focus:outline-none focus:border-primary"
            />
          </div>

          {/* API Key */}
          <div className="mb-4">
            <label className="block text-sm text-text-secondary mb-2">
              {t('llmConfig.apiKey')}
              {editing !== 'new' && <span className="text-text-muted ml-2">({t('llmConfig.apiKeyHint')})</span>}
            </label>
            <div className="relative">
              <input
                type={showApiKey ? 'text' : 'password'}
                value={formData.api_key}
                onChange={(e) => setFormData({ ...formData, api_key: e.target.value })}
                placeholder={t('llmConfig.apiKeyPlaceholder')}
                className="w-full px-3 py-2 pr-10 bg-sidebar-dark border border-slate-border rounded-lg text-text-primary text-sm font-mono focus:outline-none focus:border-primary"
              />
              <button
                type="button"
                onClick={() => setShowApiKey(!showApiKey)}
                className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-text-muted hover:text-text-primary"
              >
                {showApiKey ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          {/* Description */}
          <div className="mb-4">
            <label className="block text-sm text-text-secondary mb-2">{t('llmConfig.description')}</label>
            <input
              type="text"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder={t('llmConfig.descriptionPlaceholder')}
              className="w-full px-3 py-2 bg-sidebar-dark border border-slate-border rounded-lg text-text-primary text-sm focus:outline-none focus:border-primary"
            />
          </div>

          {/* Advanced Settings Toggle */}
          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="flex items-center gap-2 text-sm text-text-secondary hover:text-text-primary mb-4"
          >
            {showAdvanced ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            {t('llmConfig.advancedSettings')}
          </button>

          {/* Advanced Settings */}
          {showAdvanced && (
            <div className="space-y-4 p-4 bg-sidebar-dark rounded-lg border border-slate-border/50">
              {/* Enable Thinking */}
              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="enable_thinking"
                  checked={formData.enable_thinking}
                  onChange={(e) => setFormData({ ...formData, enable_thinking: e.target.checked })}
                  className="w-4 h-4 rounded border-slate-border text-primary focus:ring-primary"
                />
                <label htmlFor="enable_thinking" className="text-sm text-text-secondary">
                  {t('llmConfig.enableThinking')}
                </label>
              </div>

              {/* Support Multimodal */}
              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="support_multimodal"
                  checked={formData.support_multimodal}
                  onChange={(e) => setFormData({ ...formData, support_multimodal: e.target.checked })}
                  className="w-4 h-4 rounded border-slate-border text-primary focus:ring-primary"
                />
                <label htmlFor="support_multimodal" className="text-sm text-text-secondary">
                  {t('llmConfig.supportMultimodal')}
                </label>
                <span className="text-xs text-text-muted">
                  ({t('llmConfig.multimodalHint')})
                </span>
              </div>

              {/* Thinking Budget (Anthropic) */}
              {formData.enable_thinking && formData.provider === 'anthropic' && (
                <div>
                  <label className="block text-sm text-text-secondary mb-2">{t('llmConfig.thinkingBudget')}</label>
                  <input
                    type="number"
                    min="1024"
                    max="32000"
                    value={formData.thinking_budget_tokens}
                    onChange={(e) => setFormData({ ...formData, thinking_budget_tokens: parseInt(e.target.value) || 4096 })}
                    className="w-full px-3 py-2 bg-main-bg border border-slate-border rounded-lg text-text-primary text-sm focus:outline-none focus:border-primary"
                  />
                </div>
              )}

              {/* Reasoning Effort (OpenAI) */}
              {formData.enable_thinking && formData.provider === 'openai' && (
                <div>
                  <label className="block text-sm text-text-secondary mb-2">{t('llmConfig.reasoningEffort')}</label>
                  <Select
                    value={formData.reasoning_effort}
                    onChange={(val) => setFormData({ ...formData, reasoning_effort: val })}
                    options={[
                      { value: 'none', label: 'None', icon: 'block', iconColor: 'text-gray-400', subtitle: 'No reasoning' },
                      { value: 'low', label: 'Low', icon: 'signal_cellular_1_bar', iconColor: 'text-blue-400', subtitle: 'Light reasoning' },
                      { value: 'medium', label: 'Medium', icon: 'signal_cellular_3_bar', iconColor: 'text-green-400', subtitle: 'Balanced' },
                      { value: 'high', label: 'High', icon: 'signal_cellular_alt', iconColor: 'text-orange-400', subtitle: 'Deep reasoning' },
                      { value: 'xhigh', label: 'Extra High', icon: 'whatshot', iconColor: 'text-red-400', subtitle: 'Maximum effort' },
                    ]}
                  />
                </div>
              )}
            </div>
          )}

          {/* Form Error */}
          {formError && (
            <div className="mt-4 p-2 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
              {formError}
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 mt-4">
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

      {/* Config 列表 */}
      {!loading && !editing && (
        <div className="flex-1 overflow-y-auto custom-scrollbar">
          {configs.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-text-muted">
              <Bot size={48} className="mb-4 opacity-50" />
              <p className="text-sm">{t('llmConfig.noConfigs')}</p>
            </div>
          ) : (
            <div className="space-y-3">
              {configs.map((item) => {
                const { icon, iconColor, logo, label } = getProviderInfo(item.provider);
                const isActive = item.config_name === activeConfig;
                return (
                  <div
                    key={item.config_name}
                    className={`p-4 bg-card-bg border rounded-xl transition-colors ${
                      isActive ? 'border-primary/50 bg-primary/5' : 'border-slate-border hover:border-primary/30'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      {/* Left: Config info */}
                      <div className="flex items-start gap-3">
                        <div className="w-8 h-8 flex items-center justify-center">
                          {logo ? (
                            <img
                              src={logo}
                              alt={label}
                              className="w-6 h-6 object-contain"
                              onError={(e) => {
                                // 隐藏图片，显示 fallback
                                e.target.style.display = 'none';
                                const fallback = e.target.nextSibling;
                                if (fallback) fallback.style.display = 'inline';
                              }}
                            />
                          ) : null}
                          <span
                            className={`material-symbols-outlined text-2xl ${iconColor}`}
                            style={{ display: logo ? 'none' : 'inline' }}
                          >
                            {icon}
                          </span>
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <h4 className="text-sm font-medium text-text-primary">{item.config_name}</h4>
                            {isActive && (
                              <span className="flex items-center gap-1 text-xs px-2 py-0.5 bg-primary/10 text-primary rounded-full">
                                <CheckCircle size={12} />
                                {t('llmConfig.active')}
                              </span>
                            )}
                          </div>
                          <p className="text-xs text-text-muted mt-0.5">{label} · {item.model_name}</p>
                          <div className="flex items-center gap-3 mt-1.5">
                            {item.enable_thinking && (
                              <span className="text-xs text-purple-400 flex items-center gap-1">
                                <Zap size={12} />
                                {t('llmConfig.thinking')}
                              </span>
                            )}
                            {item.support_multimodal && (
                              <span className="text-xs text-cyan-400 flex items-center gap-1">
                                <span className="material-symbols-outlined text-sm">image</span>
                                {t('llmConfig.multimodal')}
                              </span>
                            )}
                            <span className="text-xs text-text-muted">
                              {t('settings.updatedAt')}: {formatDate(item.updated_at)}
                            </span>
                          </div>
                          {item.description && (
                            <p className="text-xs text-text-muted mt-2">{item.description}</p>
                          )}
                        </div>
                      </div>

                      {/* Right: Actions */}
                      <div className="flex items-center gap-2">
                        {!isActive && (
                          <button
                            onClick={() => handleActivate(item.config_name)}
                            className="p-2 text-text-muted hover:text-primary hover:bg-primary/10 rounded-lg transition-colors"
                            title={t('llmConfig.activate')}
                          >
                            <CheckCircle size={16} />
                          </button>
                        )}
                        <button
                          onClick={() => handleEdit(item)}
                          className="p-2 text-text-muted hover:text-primary hover:bg-primary/10 rounded-lg transition-colors"
                          title={t('settings.edit')}
                        >
                          <Pencil size={16} />
                        </button>
                        <Popconfirm
                          title={t('llmConfig.deleteConfirm')}
                          confirmText={t('sidebar.confirm')}
                          cancelText={t('sidebar.cancel')}
                          onConfirm={() => handleDelete(item.config_name)}
                          placement="left"
                        >
                          <button
                            className="p-2 text-text-muted hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                            title={t('settings.delete')}
                          >
                            <Trash2 size={16} />
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

export default LLMConfigManager;
