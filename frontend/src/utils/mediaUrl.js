function normalizeMalformedMediaPath(url) {
  if (!url || typeof url !== 'string') return '';
  const value = url.trim();
  if (!value) return '';

  // 兼容历史错误 URL: https:///media/... 或 https://media/...
  if (/^https?:\/\/\/+media\//i.test(value)) {
    return value.replace(/^https?:\/\/\/+media\//i, '/media/');
  }
  if (/^https?:\/\/media\//i.test(value)) {
    return value.replace(/^https?:\/\/media\//i, '/media/');
  }

  // 兼容绝对本地地址，统一改为相对路径，避免端口变更后失效
  if (/^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?\/media\//i.test(value)) {
    return value.replace(/^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?\/media\//i, '/media/');
  }

  if (value.startsWith('media/')) {
    return `/${value}`;
  }

  return value;
}

export function normalizeMediaUrl(url) {
  return normalizeMalformedMediaPath(url);
}

function replaceBreakTag(value) {
  if (typeof value !== 'string') return value;
  return value.replace(/\(break\)/gi, '(breath)');
}

function isBrowser() {
  return typeof window !== 'undefined';
}

function getBackendOriginForMedia() {
  if (!isBrowser()) return '';
  const configured = import.meta.env?.VITE_BACKEND_ORIGIN;
  if (configured && typeof configured === 'string') {
    return configured.replace(/\/+$/, '');
  }
  return `http://${window.location.hostname}:8001`;
}

export function toPlayableMediaUrl(url) {
  const normalized = normalizeMediaUrl(url);
  if (!normalized) return '';
  if (!isBrowser()) return normalized;

  // 开发环境下优先直连后端媒体地址，绕过 dev proxy 对 Range/206 的兼容差异
  if (normalized.startsWith('/media/') && window.location.port !== '8001') {
    return `${getBackendOriginForMedia()}${normalized}`;
  }
  return normalized;
}

export function normalizeVoiceItem(item = {}) {
  const expressionProfile = item.expressionProfile || item.expression_profile || undefined;
  if (expressionProfile && Array.isArray(expressionProfile.effect_tags)) {
    expressionProfile.effect_tags = expressionProfile.effect_tags.map((tag) => replaceBreakTag(tag));
  }
  return {
    ...item,
    sourceUrl: normalizeMediaUrl(item.sourceUrl),
    sampleAudioUrl: normalizeMediaUrl(item.sampleAudioUrl),
    fullAudioUrl: normalizeMediaUrl(item.fullAudioUrl),
    clipAudioUrl: normalizeMediaUrl(item.clipAudioUrl),
    expressionProfile,
  };
}

export function normalizeSpeechItem(item = {}) {
  const toneTags = Array.isArray(item.toneTags)
    ? item.toneTags
    : (Array.isArray(item.tone_tags) ? item.tone_tags : []);
  const effectTags = Array.isArray(item.effectTags)
    ? item.effectTags
    : (Array.isArray(item.effect_tags) ? item.effect_tags : []);
  return {
    ...item,
    audioUrl: normalizeMediaUrl(item.audioUrl || item.audio_url),
    speed: typeof item.speed === 'number' ? item.speed : undefined,
    emotion: typeof item.emotion === 'string' ? item.emotion : '',
    toneTags,
    effectTags,
    taggedText: replaceBreakTag(item.taggedText || item.tagged_text || ''),
    text: replaceBreakTag(item.text || ''),
    taggedSource: item.taggedSource || item.tagged_source || '',
    sentenceEmotions: Array.isArray(item.sentenceEmotions)
      ? item.sentenceEmotions
      : (Array.isArray(item.sentence_emotions) ? item.sentence_emotions : []),
    autoEmotion: typeof item.autoEmotion === 'boolean' ? item.autoEmotion : item.auto_emotion,
    autoBreaks: typeof item.autoBreaks === 'boolean' ? item.autoBreaks : item.auto_breaks,
    voiceProfile: item.voiceProfile || item.voice_profile || undefined,
  };
}

export function normalizeGenerationItem(item = {}) {
  return {
    ...item,
    outputUrl: normalizeMediaUrl(item.outputUrl),
  };
}

export function normalizeAvatarItem(item = {}) {
  return {
    ...item,
    sourceUrl: normalizeMediaUrl(item.sourceUrl),
    fullVideoUrl: normalizeMediaUrl(item.fullVideoUrl),
    clipVideoUrl: normalizeMediaUrl(item.clipVideoUrl),
  };
}
