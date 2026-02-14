/**
 * 工具常量模块
 * 统一管理工具图标、标签和映射关系
 *
 * 后端核心工具:
 * - parse_link: 解析链接，识别平台和内容ID
 * - fetch_content: 获取内容详情
 * - process_video: 下载视频 + 提取音频 + ASR 转录
 * - voice_clone: 语音克隆
 * - text_to_speech: 文本转语音
 * - lipsync_generate: 唇形同步
 *
 * 分析和灵感生成由 Agent 直接通过 System Prompt 完成，不再作为独立工具。
 *
 * 使用直接导入避免 lucide-react barrel file 的性能问题
 * @see https://vercel.com/blog/how-we-optimized-package-imports-in-next-js
 */
import Link from 'lucide-react/dist/esm/icons/link';
import Download from 'lucide-react/dist/esm/icons/download';
import Mic from 'lucide-react/dist/esm/icons/mic';
import Wrench from 'lucide-react/dist/esm/icons/wrench';

/**
 * 工具配置
 *
 * 注意：label 和 completedLabel 使用 i18n 翻译 key
 * 使用方式：t(`tools.${toolName}.label`)
 *
 * @type {Record<string, {icon: React.ComponentType, i18nKey: string}>}
 */
export const TOOLS = {
  parse_link: {
    icon: Link,
    i18nKey: 'tools.parse_link',
  },
  fetch_content: {
    icon: Download,
    i18nKey: 'tools.fetch_content',
  },
  process_video: {
    icon: Mic,
    i18nKey: 'tools.process_video',
  },
  voice_clone: {
    icon: Mic,
    i18nKey: 'tools.voice_clone',
  },
  text_to_speech: {
    icon: Mic,
    i18nKey: 'tools.text_to_speech',
  },
  lipsync_generate: {
    icon: Download,
    i18nKey: 'tools.lipsync_generate',
  },
};

/**
 * 默认工具图标（当工具未在 TOOLS 中定义时使用）
 */
export const DEFAULT_TOOL_ICON = Wrench;

/**
 * Stage 到 Tool 的映射
 * 用于将后端的 stage 事件转换为对应的工具
 *
 * 注意: analyzing 和 generating 阶段现在由 Agent 直接处理，
 * 不再映射到独立工具
 */
export const STAGE_TO_TOOL = {
  parsing: 'parse_link',
  fetching: 'fetch_content',
  downloading: 'process_video',
  transcribing: 'process_video',
  voice_cloning: 'voice_clone',
  tts_generating: 'text_to_speech',
  lipsync_generating: 'lipsync_generate',
};

/**
 * 获取工具信息
 * @param {string} toolName - 工具名称
 * @param {Function} t - i18n 翻译函数
 * @returns {{icon: React.ComponentType, label: string, completedLabel: string}}
 */
export function getToolInfo(toolName, t) {
  const tool = TOOLS[toolName];
  if (tool && t) {
    return {
      icon: tool.icon,
      label: t(`${tool.i18nKey}.label`),
      completedLabel: t(`${tool.i18nKey}.completedLabel`),
    };
  }
  if (tool) {
    return {
      icon: tool.icon,
      label: toolName,
      completedLabel: toolName,
    };
  }
  return {
    icon: DEFAULT_TOOL_ICON,
    label: toolName,
    completedLabel: toolName,
  };
}

/**
 * 获取工具标签
 * @param {string} toolName - 工具名称
 * @param {boolean} completed - 是否已完成
 * @param {Function} t - i18n 翻译函数
 * @returns {string}
 */
export function getToolLabel(toolName, completed = false, t = null) {
  const tool = TOOLS[toolName];
  if (!tool) return toolName;
  if (!t) return toolName;
  return completed ? t(`${tool.i18nKey}.completedLabel`) : t(`${tool.i18nKey}.label`);
}

/**
 * 获取工具图标组件
 * @param {string} toolName - 工具名称
 * @returns {React.ComponentType}
 */
export function getToolIcon(toolName) {
  const tool = TOOLS[toolName];
  return tool?.icon || DEFAULT_TOOL_ICON;
}
