import { normalizeGenerationItem, normalizeMediaUrl } from './mediaUrl';

const VOICES_STORAGE_KEY = 'media_ai_voices';
const SPEECHES_STORAGE_KEY = 'media_ai_speeches';
const GENERATIONS_STORAGE_KEY = 'media_ai_generations';

function readJsonArray(key) {
  try {
    const raw = localStorage.getItem(key);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeJsonArray(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
}

function normalizeVoice(input = {}) {
  const voiceId = (input.voice_id || input.voiceId || '').trim();
  const sourceType = (input.source_type || input.sourceType || '').trim() || 'chat';
  const sampleAudioUrl = normalizeMediaUrl(input.sample_audio_url || input.sampleAudioUrl || '');
  const fullAudioUrl = normalizeMediaUrl(input.full_audio_url || input.fullAudioUrl || '');
  const clipAudioUrl = normalizeMediaUrl(input.clip_audio_url || input.clipAudioUrl || '');
  const sourceUrl = normalizeMediaUrl(input.source_audio_url || input.sourceAudioUrl || input.sourceUrl || '');
  const expressionProfile = input.expression_profile || input.expressionProfile || undefined;

  return {
    voiceId,
    sourceType,
    sampleAudioUrl,
    fullAudioUrl,
    clipAudioUrl,
    sourceUrl,
    expressionProfile,
    title: input.title || (voiceId ? `Chat Voice ${voiceId.slice(0, 8)}` : 'Chat Voice'),
    description: input.description || 'Generated from chat',
  };
}

function normalizeSpeech(input = {}) {
  const voiceId = (input.voice_id || input.voiceId || '').trim();
  const audioUrl = normalizeMediaUrl(input.audio_url || input.audioUrl || '');
  let format = (input.format || '').trim().toLowerCase();
  const parsedSpeed = Number(input.speed);
  const speed = Number.isFinite(parsedSpeed) && parsedSpeed > 0 ? parsedSpeed : undefined;
  const emotion = (input.emotion || '').trim();
  const toneTags = Array.isArray(input.tone_tags)
    ? input.tone_tags
    : (Array.isArray(input.toneTags) ? input.toneTags : []);
  const effectTags = Array.isArray(input.effect_tags)
    ? input.effect_tags
    : (Array.isArray(input.effectTags) ? input.effectTags : []);
  const sentenceEmotions = Array.isArray(input.sentence_emotions)
    ? input.sentence_emotions
    : (Array.isArray(input.sentenceEmotions) ? input.sentenceEmotions : []);
  if (!format && audioUrl.includes('.')) {
    format = audioUrl.split('.').pop().toLowerCase();
  }
  if (!format) format = 'mp3';

  return {
    voiceId,
    audioUrl,
    format,
    speed,
    emotion,
    toneTags,
    effectTags,
    taggedText: input.tagged_text || input.taggedText || '',
    taggedSource: input.tagged_source || input.taggedSource || '',
    sentenceEmotions,
    autoEmotion: typeof input.auto_emotion === 'boolean' ? input.auto_emotion : input.autoEmotion,
    autoBreaks: typeof input.auto_breaks === 'boolean' ? input.auto_breaks : input.autoBreaks,
    voiceProfile: input.voice_profile || input.voiceProfile || undefined,
    text: input.text || 'Generated from chat',
  };
}

function normalizeGeneration(input = {}) {
  const generationId = (input.generation_id || input.generationId || '').trim();
  const outputUrl = normalizeMediaUrl(input.output_url || input.outputUrl || '');
  return normalizeGenerationItem({
    generationId,
    outputUrl,
    model: input.model || '',
    status: input.status || '',
    videoSourceType: input.video_source_type || input.videoSourceType || '',
    audioSourceType: input.audio_source_type || input.audioSourceType || '',
    videoUrl: normalizeMediaUrl(input.video_url || input.videoUrl || ''),
    audioUrl: normalizeMediaUrl(input.audio_url || input.audioUrl || ''),
  });
}

function parseByRegex(text, pattern) {
  const m = text.match(pattern);
  return (m?.[1] || '').trim();
}

function parseVoiceFromText(text) {
  if (!text) return null;

  const voiceId = parseByRegex(text, /voice[_\s-]*id[^:：\n]*[:：]\s*`?([a-zA-Z0-9_-]{8,})`?/i);
  const sourceType = parseByRegex(text, /(?:source[_\s-]*type|来源)[^:：\n]*[:：]\s*`?([a-zA-Z0-9_-]+)`?/i);
  const sampleAudioUrl = parseByRegex(text, /sample[_\s-]*audio[_\s-]*url[^:：\n]*[:：]\s*`?([^\s`"'<>]+)/i);
  const fullAudioUrl = parseByRegex(text, /full[_\s-]*audio[_\s-]*url[^:：\n]*[:：]\s*`?([^\s`"'<>]+)/i);
  const clipAudioUrl = parseByRegex(text, /clip[_\s-]*audio[_\s-]*url[^:：\n]*[:：]\s*`?([^\s`"'<>]+)/i);

  if (!voiceId && !sampleAudioUrl && !fullAudioUrl && !clipAudioUrl) return null;

  return normalizeVoice({
    voice_id: voiceId,
    source_type: sourceType,
    sample_audio_url: sampleAudioUrl,
    full_audio_url: fullAudioUrl,
    clip_audio_url: clipAudioUrl,
  });
}

function parseTtsFromText(text) {
  if (!text) return null;

  const voiceId = parseByRegex(text, /voice[_\s-]*id[^:：\n]*[:：]\s*`?([a-zA-Z0-9_-]{8,})`?/i);
  const format = parseByRegex(text, /(?:format|格式)[^:：\n]*[:：]\s*`?([a-zA-Z0-9]+)/i);
  const speedRaw = parseByRegex(text, /speed[^:：\n]*[:：]\s*`?([0-9.]+)x?`?/i);
  const speed = Number(speedRaw);
  let audioUrl = parseByRegex(text, /(?:audio[_\s-]*url|音频文件)[^:：\n]*[:：]\s*`?([^\s`"'<>]+)/i);

  if (!audioUrl) {
    const fallback = text.match(/(https?:\/\/[^\s`"'<>]+|\/media\/[^\s`"'<>]+\.(?:mp3|wav|m4a|aac|ogg|opus))/i);
    audioUrl = fallback?.[1] || '';
  }

  if (!audioUrl) return null;

  return normalizeSpeech({
    voice_id: voiceId,
    format,
    speed: Number.isFinite(speed) ? speed : undefined,
    audio_url: audioUrl,
  });
}

function dedupeVoices(list) {
  const map = new Map();
  for (const voice of list) {
    const item = normalizeVoice(voice);
    const key = item.voiceId || item.sampleAudioUrl || item.clipAudioUrl || item.fullAudioUrl;
    if (!key) continue;
    const prev = map.get(key);
    map.set(key, { ...prev, ...item });
  }
  return Array.from(map.values());
}

function dedupeSpeeches(list) {
  const map = new Map();
  for (const speech of list) {
    const item = normalizeSpeech(speech);
    const key = item.audioUrl || `${item.voiceId}:${item.text}`;
    if (!key) continue;
    const prev = map.get(key);
    if (!prev) {
      map.set(key, item);
      continue;
    }
    const merged = { ...prev, ...item };
    if (!item.taggedText && prev.taggedText) merged.taggedText = prev.taggedText;
    if ((!item.text || item.text === 'Generated from chat') && prev.text) merged.text = prev.text;
    if ((!item.toneTags || item.toneTags.length === 0) && prev.toneTags?.length) merged.toneTags = prev.toneTags;
    if ((!item.effectTags || item.effectTags.length === 0) && prev.effectTags?.length) merged.effectTags = prev.effectTags;
    if ((!item.sentenceEmotions || item.sentenceEmotions.length === 0) && prev.sentenceEmotions?.length) {
      merged.sentenceEmotions = prev.sentenceEmotions;
    }
    map.set(key, merged);
  }
  return Array.from(map.values());
}

function collectTextBlobs(segments = []) {
  const blobs = [];
  for (const seg of segments) {
    if (!seg || typeof seg !== 'object') continue;
    if (typeof seg.content === 'string' && seg.content.trim()) blobs.push(seg.content);
    if (typeof seg.output === 'string' && seg.output.trim()) blobs.push(seg.output);
  }
  return blobs;
}

export function extractChatMediaResults(segments = [], structuredData = null) {
  const voices = [];
  const speeches = [];
  const generations = [];

  if (structuredData?.cloned_voice) {
    voices.push(normalizeVoice(structuredData.cloned_voice));
  }
  if (structuredData?.tts_result) {
    speeches.push(normalizeSpeech(structuredData.tts_result));
  }
  if (structuredData?.lipsync_result) {
    generations.push(normalizeGeneration(structuredData.lipsync_result));
  }

  for (const seg of segments) {
    if (!seg || typeof seg !== 'object') continue;
    if (seg.type === 'cloned_voice' && seg.data) {
      voices.push(normalizeVoice(seg.data));
    }
    if (seg.type === 'tts_result' && seg.data) {
      speeches.push(normalizeSpeech(seg.data));
    }
    if (seg.type === 'lipsync_result' && seg.data) {
      generations.push(normalizeGeneration(seg.data));
    }
  }

  const textBlobs = collectTextBlobs(segments);
  for (const text of textBlobs) {
    const voice = parseVoiceFromText(text);
    if (voice) voices.push(voice);

    const speech = parseTtsFromText(text);
    if (speech) speeches.push(speech);
  }

  return {
    voices: dedupeVoices(voices),
    speeches: dedupeSpeeches(speeches),
    generations: dedupeGenerations(generations),
  };
}

export function persistChatMediaResults(results) {
  if (typeof window === 'undefined') return;
  const { voices = [], speeches = [], generations = [] } = results || {};

  if (voices.length > 0) {
    const existing = readJsonArray(VOICES_STORAGE_KEY);
    let counter = 0;
    for (const voice of voices) {
      if (!voice.voiceId) continue;
      const idx = existing.findIndex((v) => v.voiceId === voice.voiceId);
      const base = idx >= 0 ? existing[idx] : {};
      const nextItem = {
        id: base.id || Date.now() + counter++,
        title: voice.title || base.title || `Chat Voice ${voice.voiceId.slice(0, 8)}`,
        description: voice.description || base.description || 'Generated from chat',
        sourceType: voice.sourceType || base.sourceType || 'chat',
        voiceId: voice.voiceId,
        sampleAudioUrl: voice.sampleAudioUrl || base.sampleAudioUrl || '',
        fullAudioUrl: voice.fullAudioUrl || base.fullAudioUrl || '',
        clipAudioUrl: voice.clipAudioUrl || base.clipAudioUrl || '',
        sourceUrl: voice.sourceUrl || base.sourceUrl || '',
        expressionProfile: voice.expressionProfile || base.expressionProfile || undefined,
        timestamp: base.timestamp || new Date().toLocaleString(),
      };
      if (idx >= 0) {
        existing[idx] = nextItem;
      } else {
        existing.unshift(nextItem);
      }
    }
    writeJsonArray(VOICES_STORAGE_KEY, existing);
  }

  if (speeches.length > 0) {
    const existing = readJsonArray(SPEECHES_STORAGE_KEY);
    let counter = 0;
    for (const speech of speeches) {
      if (!speech.audioUrl) continue;
      const idx = existing.findIndex((s) => (s.audioUrl || '') === speech.audioUrl);
      const base = idx >= 0 ? existing[idx] : {};
      const nextItem = {
        id: base.id || Date.now() + counter++,
        voiceId: speech.voiceId || base.voiceId || '',
        voiceName: base.voiceName || speech.voiceId || 'Chat TTS',
        text: speech.text || base.text || 'Generated from chat',
        format: speech.format || base.format || 'mp3',
        speed: speech.speed || base.speed,
        emotion: speech.emotion || base.emotion || '',
        toneTags: speech.toneTags || base.toneTags || [],
        effectTags: speech.effectTags || base.effectTags || [],
        taggedText: speech.taggedText || base.taggedText || '',
        taggedSource: speech.taggedSource || base.taggedSource || '',
        sentenceEmotions: speech.sentenceEmotions || base.sentenceEmotions || [],
        autoEmotion: typeof speech.autoEmotion === 'boolean' ? speech.autoEmotion : base.autoEmotion,
        autoBreaks: typeof speech.autoBreaks === 'boolean' ? speech.autoBreaks : base.autoBreaks,
        voiceProfile: speech.voiceProfile || base.voiceProfile || undefined,
        audioUrl: speech.audioUrl,
        timestamp: base.timestamp || new Date().toLocaleString(),
      };
      if (idx >= 0) {
        existing[idx] = nextItem;
      } else {
        existing.unshift(nextItem);
      }
    }
    writeJsonArray(SPEECHES_STORAGE_KEY, existing);
  }

  if (generations.length > 0) {
    const existing = readJsonArray(GENERATIONS_STORAGE_KEY);
    let counter = 0;
    for (const generation of generations) {
      if (!generation.generationId && !generation.outputUrl) continue;
      const key = generation.generationId || generation.outputUrl;
      const idx = existing.findIndex((item) => (item.generationId || item.outputUrl) === key);
      const base = idx >= 0 ? existing[idx] : {};
      const nextItem = {
        id: base.id || Date.now() + counter++,
        generationId: generation.generationId || base.generationId || '',
        outputUrl: generation.outputUrl || base.outputUrl || '',
        model: generation.model || base.model || '',
        status: generation.status || base.status || '',
        videoSourceType: generation.videoSourceType || base.videoSourceType || '',
        audioSourceType: generation.audioSourceType || base.audioSourceType || '',
        videoUrl: generation.videoUrl || base.videoUrl || '',
        audioUrl: generation.audioUrl || base.audioUrl || '',
        timestamp: base.timestamp || new Date().toLocaleString(),
      };
      if (idx >= 0) {
        existing[idx] = nextItem;
      } else {
        existing.unshift(nextItem);
      }
    }
    writeJsonArray(GENERATIONS_STORAGE_KEY, existing);
  }
}

function dedupeGenerations(list) {
  const map = new Map();
  for (const generation of list) {
    const item = normalizeGeneration(generation);
    const key = item.generationId || item.outputUrl;
    if (!key) continue;
    const prev = map.get(key);
    if (!prev) {
      map.set(key, item);
      continue;
    }
    map.set(key, { ...prev, ...item });
  }
  return Array.from(map.values());
}
