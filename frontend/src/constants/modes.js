/**
 * 内容分析模式配置
 *
 * 与后端 prompts.py 中的 MODE_PROMPTS 对应：
 * - summarize: 精华提炼
 * - analyze: 深度拆解
 * - template: 模板学习
 * - style_explore: 风格探索
 *
 * 注意：模式现在从数据库动态加载，这里保留静态备份用于离线/回退场景
 * 使用方式：t(`modes.${mode.id}.label`) 或直接使用 mode.label
 */

/**
 * 静态模式定义（作为回退）
 * @type {Array<{id: string, i18nKey: string, icon: string, color: string}>}
 */
export const INSIGHT_MODES = [
  {
    id: 'summarize',
    i18nKey: 'modes.summarize',
    icon: 'format_list_bulleted',
    color: 'cyan',
  },
  {
    id: 'analyze',
    i18nKey: 'modes.analyze',
    icon: 'layers',
    color: 'orange',
  },
  {
    id: 'template',
    i18nKey: 'modes.template',
    icon: 'article',
    color: 'pink',
  },
  {
    id: 'style_explore',
    i18nKey: 'modes.style_explore',
    icon: 'palette',
    color: 'purple',
  },
];

/**
 * 默认模式 - 深度拆解
 */
export const DEFAULT_MODE = INSIGHT_MODES.find(m => m.id === 'analyze') || INSIGHT_MODES[0];

/**
 * 缓存的动态模式列表
 */
let _cachedModes = null;
let _cacheTimestamp = 0;
const CACHE_TTL = 5 * 60 * 1000; // 5 分钟缓存

/**
 * 从 API 获取动态模式列表（带缓存）
 *
 * @returns {Promise<Array>} 模式列表
 */
export async function fetchDynamicModes() {
  const now = Date.now();

  // 检查缓存
  if (_cachedModes && (now - _cacheTimestamp) < CACHE_TTL) {
    return _cachedModes;
  }

  try {
    const response = await fetch('/api/v1/remix/modes');
    if (!response.ok) {
      throw new Error(`Failed to fetch modes: ${response.status}`);
    }
    const data = await response.json();

    // 转换为标准格式
    const modes = (data.modes || []).map(mode => ({
      id: mode.value,
      i18nKey: `modes.${mode.value}`,
      icon: mode.icon || 'smart_toy',
      color: mode.color || 'cyan',
      // 动态模式直接包含翻译后的文本
      label: mode.label,
      description: mode.description,
      prefill: mode.prefill,
    }));

    // 更新缓存
    _cachedModes = modes;
    _cacheTimestamp = now;

    return modes;
  } catch (err) {
    console.warn('Failed to fetch dynamic modes, using fallback:', err);
    return INSIGHT_MODES;
  }
}

/**
 * 使缓存失效（在模式配置更新后调用）
 */
export function invalidateModesCache() {
  _cachedModes = null;
  _cacheTimestamp = 0;
}

/**
 * 颜色样式映射
 */
export const MODE_COLOR_CLASSES = {
  cyan: {
    icon: 'bg-accent-cyan/15 text-accent-cyan',
    hover: 'hover:border-accent-cyan/30 hover:shadow-[0_0_20px_rgba(6,182,212,0.15)]',
    border: 'border-accent-cyan/30',
    text: 'text-accent-cyan',
  },
  orange: {
    icon: 'bg-accent-orange/15 text-accent-orange',
    hover: 'hover:border-accent-orange/30 hover:shadow-[0_0_20px_rgba(249,115,22,0.15)]',
    border: 'border-accent-orange/30',
    text: 'text-accent-orange',
  },
  pink: {
    icon: 'bg-accent-pink/15 text-accent-pink',
    hover: 'hover:border-accent-pink/30 hover:shadow-[0_0_20px_rgba(236,72,153,0.15)]',
    border: 'border-accent-pink/30',
    text: 'text-accent-pink',
  },
  purple: {
    icon: 'bg-accent-purple/15 text-accent-purple',
    hover: 'hover:border-accent-purple/30 hover:shadow-[0_0_20px_rgba(168,85,247,0.15)]',
    border: 'border-accent-purple/30',
    text: 'text-purple-400',
  },
};

/**
 * 根据 mode id 获取模式配置
 * @param {string} modeId
 * @returns {object|undefined}
 */
export function getModeById(modeId) {
  return INSIGHT_MODES.find(m => m.id === modeId);
}
