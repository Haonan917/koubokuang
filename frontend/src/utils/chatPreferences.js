import { normalizeAvatarItem, normalizeVoiceItem } from './mediaUrl';
import { LLM_MODEL_OPTIONS } from '../constants/llmModels';

const VOICES_STORAGE_KEY = 'media_ai_voices';
const AVATARS_STORAGE_KEY = 'media_ai_avatars';
const CHAT_PREFS_KEY = 'media_ai_chat_preferences';

function readJsonArray(key) {
  try {
    const raw = localStorage.getItem(key);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function readVoiceList() {
  return readJsonArray(VOICES_STORAGE_KEY).map((item) => normalizeVoiceItem(item));
}

export function readAvatarList() {
  return readJsonArray(AVATARS_STORAGE_KEY).map((item) => normalizeAvatarItem(item));
}

export function readChatPreferences() {
  try {
    const raw = localStorage.getItem(CHAT_PREFS_KEY);
    const parsed = raw ? JSON.parse(raw) : {};
    return {
      voiceId: typeof parsed.voiceId === 'string' ? parsed.voiceId : '',
      avatarId: typeof parsed.avatarId === 'string' ? parsed.avatarId : '',
      modelName: typeof parsed.modelName === 'string' ? parsed.modelName : '',
    };
  } catch {
    return { voiceId: '', avatarId: '', modelName: '' };
  }
}

export function writeChatPreferences(next) {
  const payload = {
    voiceId: next?.voiceId || '',
    avatarId: next?.avatarId || '',
    modelName: next?.modelName || '',
  };
  localStorage.setItem(CHAT_PREFS_KEY, JSON.stringify(payload));
}

export function ensureChatPreferences() {
  const voices = readVoiceList();
  const avatars = readAvatarList();
  const pref = readChatPreferences();

  const findAvatar = (avatarId) => avatars.find((a) => a.avatarId === avatarId || String(a.id) === String(avatarId));

  let voiceId = pref.voiceId;
  if (voiceId && !voices.find((v) => v.voiceId === voiceId)) {
    voiceId = '';
  }
  if (!voiceId && voices.length > 0) {
    voiceId = voices[0].voiceId;
  }

  let avatarId = pref.avatarId;
  if (avatarId && !findAvatar(avatarId)) {
    avatarId = '';
  }
  if (!avatarId && avatars.length > 0) {
    avatarId = avatars[0].avatarId || String(avatars[0].id || '');
  }

  if (voiceId !== pref.voiceId || avatarId !== pref.avatarId) {
    writeChatPreferences({ voiceId, avatarId, modelName: pref.modelName });
  }

  const selectedVoice = voices.find((v) => v.voiceId === voiceId) || null;
  const selectedAvatar = findAvatar(avatarId) || null;
  const allowedModels = Array.isArray(LLM_MODEL_OPTIONS) ? LLM_MODEL_OPTIONS : [];
  let modelName = pref.modelName;
  if (modelName && !allowedModels.find((m) => m.value === modelName)) {
    modelName = '';
  }
  if (!modelName && allowedModels.length > 0) {
    modelName = allowedModels[0].value;
  }
  if (modelName !== pref.modelName) {
    writeChatPreferences({ voiceId, avatarId, modelName });
  }

  return {
    voices,
    avatars,
    selectedVoice,
    selectedAvatar,
    voiceId,
    avatarId,
    modelName,
  };
}

export function resolveChatPreferredPayload() {
  const { selectedVoice, selectedAvatar, voiceId, avatarId, modelName } = ensureChatPreferences();
  const preferredAvatarUrl = selectedAvatar?.clipVideoUrl || selectedAvatar?.fullVideoUrl || '';

  return {
    preferredVoiceId: voiceId || '',
    preferredVoiceTitle: selectedVoice?.title || '',
    preferredAvatarId: avatarId || '',
    preferredAvatarTitle: selectedAvatar?.title || '',
    preferredAvatarUrl: preferredAvatarUrl || '',
    preferredModelName: modelName || '',
  };
}
