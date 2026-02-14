import React, { useMemo, useRef, useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { previewTtsTags, textToSpeech, fetchMediaAiVoices, fetchMediaAiTtsResults } from '../../services/api';
import { normalizeMediaUrl, normalizeSpeechItem, normalizeVoiceItem, toPlayableMediaUrl } from '../../utils/mediaUrl';
import { ADVANCED_EMOTION_TAGS, BASIC_EMOTION_TAGS, EFFECT_TAGS, TONE_TAGS } from '../../utils/ttsTags';

const VOICES_STORAGE_KEY = 'media_ai_voices';
const SPEECHES_STORAGE_KEY = 'media_ai_speeches';

function readStorage(key) {
  try {
    const raw = localStorage.getItem(key);
    const parsed = raw ? JSON.parse(raw) : [];
    if (!Array.isArray(parsed)) return [];
    if (key === VOICES_STORAGE_KEY) return parsed.map((item) => normalizeVoiceItem(item));
    if (key === SPEECHES_STORAGE_KEY) return parsed.map((item) => normalizeSpeechItem(item));
    return parsed;
  } catch {
    return [];
  }
}

function writeStorage(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
}

function mergeByKey(localList, remoteList, keyGetter) {
  const map = new Map();
  for (const item of [...remoteList, ...localList]) {
    const key = keyGetter(item);
    if (!key) continue;
    const prev = map.get(key) || {};
    map.set(key, { ...prev, ...item });
  }
  return Array.from(map.values());
}

function TTSManager() {
  const { t } = useTranslation();
  const textAreaRef = useRef(null);
  const taggedAreaRef = useRef(null);
  const [text, setText] = useState('');
  const [format, setFormat] = useState('mp3');
  const [speed, setSpeed] = useState(0.85);
  const useVoiceProfile = true;
  const autoEmotion = true;
  const autoBreaks = true;
  const [showTagLibrary, setShowTagLibrary] = useState(false);
  const [tagging, setTagging] = useState(false);
  const [taggedPreview, setTaggedPreview] = useState('');
  const [sentenceEmotions, setSentenceEmotions] = useState([]);
  const [voices, setVoices] = useState(() => readStorage(VOICES_STORAGE_KEY));
  const [selectedVoiceId, setSelectedVoiceId] = useState('');
  const [speeches, setSpeeches] = useState(() => readStorage(SPEECHES_STORAGE_KEY));
  const [searchQuery, setSearchQuery] = useState('');
  const [serverOffset, setServerOffset] = useState(0);
  const [serverTotal, setServerTotal] = useState(0);
  const [serverLoading, setServerLoading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const selectedVoice = useMemo(
    () => voices.find((v) => v.voiceId === selectedVoiceId),
    [voices, selectedVoiceId]
  );

  const canGenerate = text.trim().length > 0 && !!selectedVoiceId;
  const canDetectTags = text.trim().length > 0 && !!selectedVoiceId;

  const persistSpeeches = (next) => {
    setSpeeches(next);
    writeStorage(SPEECHES_STORAGE_KEY, next);
  };

  const loadFromServer = async (nextOffset = 0, queryText = '') => {
    setServerLoading(true);
    try {
      const [voicesRes, ttsRes] = await Promise.all([
        fetchMediaAiVoices(50, 0, ''),
        fetchMediaAiTtsResults(20, nextOffset, queryText),
      ]);
      const remoteVoices = Array.isArray(voicesRes?.data) ? voicesRes.data.map((item) => normalizeVoiceItem(item)) : [];
      const remoteSpeeches = Array.isArray(ttsRes?.data) ? ttsRes.data.map((item) => normalizeSpeechItem(item)) : [];
      if (remoteVoices.length > 0) {
        const mergedVoices = mergeByKey(voices, remoteVoices, (item) => item.voiceId || item.voice_id || item.sampleAudioUrl || item.fullAudioUrl);
        setVoices(mergedVoices);
        writeStorage(VOICES_STORAGE_KEY, mergedVoices);
      }
      if (remoteSpeeches.length > 0) {
        const mergedSpeeches = mergeByKey(speeches, remoteSpeeches, (item) => item.audioUrl || item.audio_url);
        persistSpeeches(mergedSpeeches);
        setServerOffset(nextOffset + remoteSpeeches.length);
      }
      setServerTotal(Number(ttsRes?.total || 0));
    } catch {
      // ignore
    } finally {
      setServerLoading(false);
    }
  };

  useEffect(() => {
    let mounted = true;
    const init = async () => {
      if (!mounted) return;
      setServerOffset(0);
      setServerTotal(0);
      await loadFromServer(0, searchQuery);
    };
    init();
    return () => {
      mounted = false;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchQuery]);

  const filteredSpeeches = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return speeches;
    return speeches.filter((speech) => {
      const hay = [
        speech.voiceName,
        speech.voiceId,
        speech.text,
        speech.taggedText,
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();
      return hay.includes(q);
    });
  }, [speeches, searchQuery]);

  const insertTagToPreview = (tag) => {
    const baseText = taggedPreview || text;
    if (!baseText) return;
    const textarea = taggedAreaRef.current;
    if (!textarea || !taggedPreview) {
      const spacer = baseText && !baseText.endsWith(' ') ? ' ' : '';
      setTaggedPreview(`${baseText}${spacer}${tag} `);
      return;
    }
    const start = textarea.selectionStart ?? taggedPreview.length;
    const end = textarea.selectionEnd ?? taggedPreview.length;
    const before = taggedPreview.slice(0, start);
    const after = taggedPreview.slice(end);
    const spacerBefore = before && !before.endsWith(' ') ? ' ' : '';
    const next = `${before}${spacerBefore}${tag} ${after}`;
    setTaggedPreview(next);
    requestAnimationFrame(() => {
      const pos = (before + spacerBefore + `${tag} `).length;
      textarea.focus();
      textarea.setSelectionRange(pos, pos);
    });
  };

  const handleDetectTags = async () => {
    if (!canDetectTags || tagging) return;
    setTagging(true);
    setError('');
    try {
      const inputText = text.trim();
      const result = await previewTtsTags({
        voiceId: selectedVoiceId,
        text: inputText,
        autoEmotion,
        autoBreaks,
        tagStrategy: 'llm',
        speechStyle: 'speech',
        useVoiceProfile,
      });
      const preview = result?.data?.tagged_text || result?.data?.text || inputText;
      setTaggedPreview(preview);
      setSentenceEmotions(Array.isArray(result?.data?.sentence_emotions) ? result.data.sentence_emotions : []);
    } catch (e) {
      setError(e.message || 'Tag detection failed');
    } finally {
      setTagging(false);
    }
  };

  const handleGenerate = async () => {
    if (!canGenerate || loading) return;
    setLoading(true);
    setError('');
    try {
      const inputText = text.trim();
      const previewText = taggedPreview.trim();
      const synthText = previewText || inputText;
      const usingPreview = !!previewText;
      const tagMode = usingPreview ? 'manual' : 'none';
      const result = await textToSpeech({
        voiceId: selectedVoiceId,
        text: synthText,
        audioFormat: format,
        speed,
        autoEmotion: false,
        autoBreaks: false,
        tagStrategy: 'none',
        speechStyle: 'speech',
        useVoiceProfile: usingPreview ? false : useVoiceProfile,
      });
      const item = {
        id: Date.now(),
        voiceId: selectedVoiceId,
        voiceName: selectedVoice?.title || selectedVoiceId,
        text: inputText,
        format,
        speed: Number(result?.data?.speed ?? speed),
        emotion: '',
        toneTags: [],
        effectTags: [],
        autoEmotion: result?.data?.auto_emotion,
        autoBreaks: result?.data?.auto_breaks,
        sentenceEmotions: result?.data?.sentence_emotions || sentenceEmotions,
        taggedText: usingPreview ? synthText : '',
        taggedSource: tagMode,
        voiceProfile: result?.data?.voice_profile || undefined,
        audioUrl: normalizeMediaUrl(result?.data?.audio_url || result?.data?.audioUrl),
        timestamp: new Date().toLocaleString(),
      };
      persistSpeeches([item, ...speeches]);
    } catch (e) {
      setError(e.message || 'TTS failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-xl font-semibold text-text-primary">{t('mediaAi.ttsTitle')}</h3>
        <p className="text-sm text-text-muted mt-1">{t('mediaAi.ttsDesc')}</p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div className="border border-border-default rounded-xl p-4 space-y-4">
          <div>
            <label className="text-sm font-medium text-text-secondary">{t('mediaAi.selectVoice')}</label>
            <select
              value={selectedVoiceId}
              onChange={(e) => {
                setSelectedVoiceId(e.target.value);
                setTaggedPreview('');
                setSentenceEmotions([]);
              }}
              className="mt-2 w-full bg-bg-tertiary border border-border-default rounded-lg px-3 py-2 text-sm"
            >
              <option value="">{t('mediaAi.selectVoicePlaceholder')}</option>
              {voices.map((voice) => (
                <option key={voice.voiceId} value={voice.voiceId}>
                  {voice.title || voice.voiceId}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-sm font-medium text-text-secondary">{t('mediaAi.format')}</label>
            <select
              value={format}
              onChange={(e) => setFormat(e.target.value)}
              className="mt-2 w-full bg-bg-tertiary border border-border-default rounded-lg px-3 py-2 text-sm"
            >
              <option value="mp3">MP3</option>
              <option value="wav">WAV</option>
            </select>
          </div>

          <div>
            <label className="text-sm font-medium text-text-secondary">{t('mediaAi.ttsSpeed')}</label>
            <div className="mt-2 flex items-center gap-3">
              <input
                type="range"
                min="0.5"
                max="2"
                step="0.05"
                value={speed}
                onChange={(e) => setSpeed(Number(e.target.value))}
                className="w-full"
              />
              <input
                type="number"
                min="0.5"
                max="2"
                step="0.05"
                value={speed}
                onChange={(e) => {
                  const next = Number(e.target.value);
                  if (!Number.isFinite(next)) return;
                  setSpeed(Math.max(0.5, Math.min(2, next)));
                }}
                className="w-24 bg-bg-tertiary border border-border-default rounded-lg px-2 py-1 text-sm"
              />
            </div>
            <p className="text-xs text-text-muted mt-1">{t('mediaAi.ttsSpeedHint')}</p>
          </div>

          <div>
            <label className="text-sm font-medium text-text-secondary">{t('mediaAi.scriptText')}</label>
            <textarea
              ref={textAreaRef}
              value={text}
              onChange={(e) => {
                setText(e.target.value);
                setTaggedPreview('');
                setSentenceEmotions([]);
              }}
              className="mt-2 w-full bg-bg-tertiary border border-border-default rounded-lg px-3 py-2 text-sm min-h-[180px]"
              placeholder={t('mediaAi.scriptPlaceholder')}
              maxLength={5000}
            />
            <p className="text-xs text-text-muted mt-1">{text.length}/5000</p>
            <div className="mt-2">
              <button
                type="button"
                onClick={handleDetectTags}
                disabled={!canDetectTags || tagging}
                className="px-3 py-2 rounded-lg text-sm border border-border-default disabled:opacity-50"
              >
                {tagging ? t('mediaAi.processing') : t('mediaAi.detectExpressionTags')}
              </button>
            </div>
            <div className="mt-2 flex flex-wrap gap-2">
              <button type="button" onClick={() => insertTagToPreview('(breath)')} className="px-2.5 py-1 rounded-md text-xs border border-border-default text-text-muted">{t('mediaAi.insertBreath')}</button>
              <button type="button" onClick={() => insertTagToPreview('(long-break)')} className="px-2.5 py-1 rounded-md text-xs border border-border-default text-text-muted">{t('mediaAi.insertLongBreak')}</button>
              <button type="button" onClick={() => insertTagToPreview('(laughing)')} className="px-2.5 py-1 rounded-md text-xs border border-border-default text-text-muted">{t('mediaAi.insertLaugh')}</button>
              <button type="button" onClick={() => setShowTagLibrary((v) => !v)} className="px-2.5 py-1 rounded-md text-xs border border-border-default text-text-muted">{t('mediaAi.tagLibrary')}</button>
            </div>
            {showTagLibrary && (
              <div className="mt-3 border border-border-default rounded-lg p-3 space-y-3">
                <p className="text-xs text-text-muted">{t('mediaAi.tagLibraryHint')}</p>
                <div className="space-y-2">
                  <p className="text-xs font-medium text-text-secondary">{t('mediaAi.ttsEmotionBasic')}</p>
                  <div className="flex flex-wrap gap-2">
                    {BASIC_EMOTION_TAGS.map((tag) => (
                      <button key={tag} type="button" onClick={() => insertTagToPreview(tag)} className="px-2 py-1 rounded-md text-xs border border-border-default text-text-muted">{tag}</button>
                    ))}
                  </div>
                </div>
                <div className="space-y-2">
                  <p className="text-xs font-medium text-text-secondary">{t('mediaAi.ttsEmotionAdvanced')}</p>
                  <div className="flex flex-wrap gap-2">
                    {ADVANCED_EMOTION_TAGS.map((tag) => (
                      <button key={tag} type="button" onClick={() => insertTagToPreview(tag)} className="px-2 py-1 rounded-md text-xs border border-border-default text-text-muted">{tag}</button>
                    ))}
                  </div>
                </div>
                <div className="space-y-2">
                  <p className="text-xs font-medium text-text-secondary">{t('mediaAi.ttsToneTags')}</p>
                  <div className="flex flex-wrap gap-2">
                    {TONE_TAGS.map((tag) => (
                      <button key={tag} type="button" onClick={() => insertTagToPreview(tag)} className="px-2 py-1 rounded-md text-xs border border-border-default text-text-muted">{tag}</button>
                    ))}
                  </div>
                </div>
                <div className="space-y-2">
                  <p className="text-xs font-medium text-text-secondary">{t('mediaAi.ttsEffectTags')}</p>
                  <div className="flex flex-wrap gap-2">
                    {EFFECT_TAGS.map((tag) => (
                      <button key={tag} type="button" onClick={() => insertTagToPreview(tag)} className="px-2 py-1 rounded-md text-xs border border-border-default text-text-muted">{tag}</button>
                    ))}
                  </div>
                </div>
              </div>
            )}
            {(taggedPreview || tagging) && (
              <div className="mt-3 border border-border-default rounded-lg p-3 space-y-2">
                <p className="text-xs font-medium text-text-secondary">{t('mediaAi.taggedTextPreview')}</p>
                <textarea
                  ref={taggedAreaRef}
                  value={taggedPreview}
                  onChange={(e) => setTaggedPreview(e.target.value)}
                  className="w-full bg-bg-tertiary border border-border-default rounded-lg px-3 py-2 text-xs min-h-[140px]"
                  placeholder={t('mediaAi.taggedTextPlaceholder')}
                />
                {sentenceEmotions.length > 0 && (
                  <p className="text-[11px] text-text-muted">
                    {t('mediaAi.sentenceEmotionResult')}: {sentenceEmotions.join(' | ')}
                  </p>
                )}
              </div>
            )}
          </div>

          {error && <p className="text-sm text-red-400">{error}</p>}

          <button
            onClick={handleGenerate}
            disabled={!canGenerate || loading}
            className="w-full px-4 py-2 rounded-lg bg-primary text-white disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? t('mediaAi.processing') : t('mediaAi.generateSpeech')}
          </button>
        </div>

        <div className="border border-border-default rounded-xl p-4">
          <h4 className="font-medium text-text-primary mb-3">{t('mediaAi.recentSpeeches')}</h4>
          <input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={t('mediaAi.searchPlaceholder')}
            className="mb-3 w-full bg-bg-tertiary border border-border-default rounded-lg px-3 py-2 text-sm"
          />
          <div className="space-y-3 max-h-[520px] overflow-y-auto custom-scrollbar pr-1">
            {filteredSpeeches.length === 0 && (
              <p className="text-sm text-text-muted">{t('mediaAi.noSpeeches')}</p>
            )}
            {filteredSpeeches.map((speech) => (
              <div key={speech.id} className="border border-border-default rounded-lg p-3">
                <div className="flex items-center justify-between gap-2">
                  <p className="font-medium text-sm text-text-primary">{speech.voiceName}</p>
                  <span className="text-xs text-text-muted">
                    {speech.format}
                    {typeof speech.speed === 'number' ? ` · ${speech.speed}x` : ''}
                  </span>
                </div>
                <p className="text-xs text-text-muted mt-1 line-clamp-2">
                  {speech.taggedSource === 'manual' ? (speech.taggedText || speech.text) : speech.text}
                </p>
                {speech.taggedSource === 'auto' && (speech.emotion || (speech.toneTags?.length ?? 0) > 0 || (speech.effectTags?.length ?? 0) > 0) && (
                  <p className="text-xs text-text-muted mt-1 line-clamp-2">
                    {[speech.emotion, ...(speech.toneTags || []), ...(speech.effectTags || [])].filter(Boolean).join(' ')}
                  </p>
                )}
                {speech.taggedSource !== 'manual' && speech.taggedText && speech.taggedText !== speech.text && (
                  <p className="text-[11px] text-text-muted mt-1 line-clamp-2">{speech.taggedText}</p>
                )}
                {speech.audioUrl && (
                  <audio
                    className="w-full mt-2"
                    controls
                    preload="metadata"
                    src={toPlayableMediaUrl(speech.audioUrl)}
                  />
                )}
              </div>
            ))}
            {serverOffset < serverTotal && (
              <button
                type="button"
                disabled={serverLoading}
                onClick={() => loadFromServer(serverOffset, searchQuery)}
                className="w-full px-3 py-2 rounded-lg border border-border-default text-sm disabled:opacity-50"
              >
                {serverLoading ? t('mediaAi.processing') : t('mediaAi.loadMore')}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default TTSManager;
