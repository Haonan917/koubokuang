import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { generateLipsync, getLipsyncStatus, textToSpeech, uploadAudioFile, uploadVideoFile, fetchMediaAiVoices, fetchMediaAiTtsResults, fetchMediaAiAvatars, fetchMediaAiLipsyncResults } from '../../services/api';
import { normalizeAvatarItem, normalizeGenerationItem, normalizeMediaUrl, normalizeSpeechItem, normalizeVoiceItem, toPlayableMediaUrl } from '../../utils/mediaUrl';
import TTSTagControls from './TTSTagControls';

const VOICES_STORAGE_KEY = 'media_ai_voices';
const SPEECHES_STORAGE_KEY = 'media_ai_speeches';
const GENERATIONS_STORAGE_KEY = 'media_ai_generations';
const AVATARS_STORAGE_KEY = 'media_ai_avatars';

function readStorage(key) {
  try {
    const raw = localStorage.getItem(key);
    const parsed = raw ? JSON.parse(raw) : [];
    if (!Array.isArray(parsed)) return [];
    if (key === VOICES_STORAGE_KEY) return parsed.map((item) => normalizeVoiceItem(item));
    if (key === SPEECHES_STORAGE_KEY) return parsed.map((item) => normalizeSpeechItem(item));
    if (key === GENERATIONS_STORAGE_KEY) return parsed.map((item) => normalizeGenerationItem(item));
    if (key === AVATARS_STORAGE_KEY) return parsed.map((item) => normalizeAvatarItem(item));
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

function LipsyncManager() {
  const { t } = useTranslation();
  const [videoFile, setVideoFile] = useState(null);
  const [videoUrlInput, setVideoUrlInput] = useState('');
  const [videoSourceType, setVideoSourceType] = useState('upload'); // upload | url | avatar
  const [selectedAvatarId, setSelectedAvatarId] = useState('');

  const [audioSourceType, setAudioSourceType] = useState('upload'); // upload | tts | script
  const [audioFile, setAudioFile] = useState(null);
  const [selectedSpeechId, setSelectedSpeechId] = useState('');
  const [scriptText, setScriptText] = useState('');
  const [scriptVoiceId, setScriptVoiceId] = useState('');
  const [scriptTtsSpeed, setScriptTtsSpeed] = useState(0.85);
  const [scriptUseVoiceProfile, setScriptUseVoiceProfile] = useState(true);
  const [scriptAutoEmotion, setScriptAutoEmotion] = useState(true);
  const [scriptAutoBreaks, setScriptAutoBreaks] = useState(true);
  const [scriptEmotionTag, setScriptEmotionTag] = useState('');
  const [scriptToneTags, setScriptToneTags] = useState([]);
  const [scriptEffectTags, setScriptEffectTags] = useState([]);
  const [model, setModel] = useState('lipsync-2');
  const [generations, setGenerations] = useState(() => readStorage(GENERATIONS_STORAGE_KEY));
  const [searchQuery, setSearchQuery] = useState('');
  const [serverOffset, setServerOffset] = useState(0);
  const [serverTotal, setServerTotal] = useState(0);
  const [serverLoading, setServerLoading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const pollingRef = useRef(new Map());

  const [voices, setVoices] = useState(() => readStorage(VOICES_STORAGE_KEY));
  const [speeches, setSpeeches] = useState(() => readStorage(SPEECHES_STORAGE_KEY));
  const [avatars, setAvatars] = useState(() => readStorage(AVATARS_STORAGE_KEY));
  const selectedSpeech = speeches.find((s) => String(s.id) === selectedSpeechId);
  const selectedAvatar = avatars.find((a) => String(a.id) === selectedAvatarId);

  useEffect(() => {
    if (videoSourceType === 'avatar') {
      setAvatars(readStorage(AVATARS_STORAGE_KEY));
    }
  }, [videoSourceType]);

  const loadFromServer = async (nextOffset = 0, queryText = '') => {
    setServerLoading(true);
    try {
      const [voicesRes, ttsRes, avatarsRes, lipsyncRes] = await Promise.all([
        fetchMediaAiVoices(50, 0, ''),
        fetchMediaAiTtsResults(50, 0, ''),
        fetchMediaAiAvatars(50, 0, ''),
        fetchMediaAiLipsyncResults(20, nextOffset, queryText),
      ]);
      const remoteVoices = Array.isArray(voicesRes?.data) ? voicesRes.data.map((item) => normalizeVoiceItem(item)) : [];
      const remoteSpeeches = Array.isArray(ttsRes?.data) ? ttsRes.data.map((item) => normalizeSpeechItem(item)) : [];
      const remoteAvatars = Array.isArray(avatarsRes?.data) ? avatarsRes.data.map((item) => normalizeAvatarItem(item)) : [];
      const remoteGenerations = Array.isArray(lipsyncRes?.data) ? lipsyncRes.data.map((item) => normalizeGenerationItem(item)) : [];

      if (remoteVoices.length > 0) {
        const merged = mergeByKey(voices, remoteVoices, (item) => item.voiceId || item.voice_id || item.sampleAudioUrl || item.fullAudioUrl);
        setVoices(merged);
        writeStorage(VOICES_STORAGE_KEY, merged);
      }
      if (remoteSpeeches.length > 0) {
        const merged = mergeByKey(speeches, remoteSpeeches, (item) => item.audioUrl || item.audio_url);
        setSpeeches(merged);
        writeStorage(SPEECHES_STORAGE_KEY, merged);
      }
      if (remoteAvatars.length > 0) {
        const merged = mergeByKey(avatars, remoteAvatars, (item) => item.avatarId || item.id || item.clipVideoUrl || item.fullVideoUrl);
        setAvatars(merged);
        writeStorage(AVATARS_STORAGE_KEY, merged);
      }
      if (remoteGenerations.length > 0) {
        const merged = mergeByKey(generations, remoteGenerations, (item) => item.generationId || item.outputUrl);
        setGenerations(merged);
        writeStorage(GENERATIONS_STORAGE_KEY, merged);
        setServerOffset(nextOffset + remoteGenerations.length);
      }
      setServerTotal(Number(lipsyncRes?.total || 0));
    } catch {
      // ignore
    } finally {
      setServerLoading(false);
    }
  };

  useEffect(() => {
    let mounted = true;
    const init = async () => {
      try {
        if (!mounted) return;
        setServerOffset(0);
        setServerTotal(0);
        await loadFromServer(0, searchQuery);
      } catch {
        // ignore
      }
    };
    init();
    return () => {
      mounted = false;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchQuery]);

  const filteredGenerations = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return generations;
    return generations.filter((item) => {
      const hay = [
        item.generationId,
        item.model,
        item.status,
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();
      return hay.includes(q);
    });
  }, [generations, searchQuery]);

  const persistGenerations = (next) => {
    setGenerations(next);
    writeStorage(GENERATIONS_STORAGE_KEY, next);
  };

  const stopPolling = (id) => {
    const timer = pollingRef.current.get(id);
    if (timer) {
      clearInterval(timer);
      pollingRef.current.delete(id);
    }
  };

  const startPolling = (id) => {
    if (!id || pollingRef.current.has(id)) return;
    const timer = setInterval(async () => {
      try {
        const result = await getLipsyncStatus(id);
        const data = result?.data || {};
        const status = data.status;
        const outputUrl = normalizeMediaUrl(data.outputUrl || data.outputMediaUrl || data.output_url || '');
        setGenerations((prev) => {
          const next = prev.map((item) => {
            if (item.generationId !== id) return item;
            return { ...item, status: status || item.status, outputUrl: outputUrl || item.outputUrl };
          });
          writeStorage(GENERATIONS_STORAGE_KEY, next);
          return next;
        });
        if (status === 'COMPLETED' || status === 'FAILED' || status === 'REJECTED') {
          stopPolling(id);
        }
      } catch {
        // 忽略轮询错误，等待下一轮
      }
    }, 5000);
    pollingRef.current.set(id, timer);
  };

  useEffect(() => {
    generations.forEach((item) => {
      if (item.status === 'PENDING' || item.status === 'PROCESSING') {
        startPolling(item.generationId);
      }
    });
    return () => {
      pollingRef.current.forEach((timer) => clearInterval(timer));
      pollingRef.current.clear();
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const canGenerate = useMemo(() => {
    const hasVideo = videoSourceType === 'upload'
      ? !!videoFile
      : videoSourceType === 'avatar'
        ? !!(selectedAvatar?.clipVideoUrl || selectedAvatar?.fullVideoUrl)
        : !!videoUrlInput.trim();
    if (!hasVideo) return false;
    if (audioSourceType === 'upload') return !!audioFile;
    if (audioSourceType === 'tts') return !!selectedSpeech;
    return !!scriptText.trim() && !!scriptVoiceId;
  }, [videoSourceType, videoFile, videoUrlInput, selectedAvatar, audioSourceType, audioFile, selectedSpeech, scriptText, scriptVoiceId]);

  const handleGenerate = async () => {
    if (!canGenerate || loading) return;
    setLoading(true);
    setError('');
    try {
      let videoUrl = videoUrlInput.trim();
      if (videoSourceType === 'upload') {
        const uploadedVideo = await uploadVideoFile(videoFile);
        videoUrl = uploadedVideo?.data?.url || '';
      } else if (videoSourceType === 'avatar') {
        videoUrl = selectedAvatar?.clipVideoUrl || selectedAvatar?.fullVideoUrl || '';
      }
      videoUrl = normalizeMediaUrl(videoUrl);

      let audioUrl = '';
      if (audioSourceType === 'upload') {
        const uploadedAudio = await uploadAudioFile(audioFile);
        audioUrl = uploadedAudio?.data?.url || '';
      } else if (audioSourceType === 'tts') {
        audioUrl = selectedSpeech?.audioUrl || '';
      } else {
        const ttsResult = await textToSpeech({
          voiceId: scriptVoiceId,
          text: scriptText.trim(),
          audioFormat: 'mp3',
          speed: scriptTtsSpeed,
          emotion: scriptEmotionTag,
          toneTags: scriptToneTags,
          effectTags: scriptEffectTags,
          autoEmotion: scriptAutoEmotion,
          autoBreaks: scriptAutoBreaks,
          useVoiceProfile: scriptUseVoiceProfile,
        });
        audioUrl = ttsResult?.data?.audio_url || ttsResult?.data?.audioUrl || '';
      }
      audioUrl = normalizeMediaUrl(audioUrl);

      const result = await generateLipsync({ videoUrl, audioUrl, model });
      const generationId = result?.data?.generation_id || result?.data?.id;
      const item = {
        id: Date.now(),
        generationId,
        status: result?.data?.status || 'PENDING',
        outputUrl: normalizeMediaUrl(result?.data?.output_url || result?.data?.outputUrl || result?.data?.outputMediaUrl || ''),
        model,
        videoSourceType,
        audioSourceType,
        timestamp: new Date().toLocaleString(),
      };
      const next = [item, ...generations];
      persistGenerations(next);
      startPolling(generationId);
    } catch (e) {
      setError(e.message || 'Lipsync failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-xl font-semibold text-text-primary">{t('mediaAi.lipsyncTitle')}</h3>
        <p className="text-sm text-text-muted mt-1">{t('mediaAi.lipsyncDesc')}</p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div className="border border-border-default rounded-xl p-4 space-y-4">
          <div>
            <label className="text-sm font-medium text-text-secondary">{t('mediaAi.videoSource')}</label>
            <div className="mt-2 flex gap-2">
              <button onClick={() => setVideoSourceType('upload')} className={`px-3 py-2 rounded-lg text-sm border ${videoSourceType === 'upload' ? 'bg-primary/10 border-primary/40 text-primary' : 'border-border-default text-text-secondary'}`}>{t('mediaAi.uploadVideo')}</button>
              <button onClick={() => setVideoSourceType('url')} className={`px-3 py-2 rounded-lg text-sm border ${videoSourceType === 'url' ? 'bg-primary/10 border-primary/40 text-primary' : 'border-border-default text-text-secondary'}`}>{t('mediaAi.videoUrl')}</button>
              <button onClick={() => setVideoSourceType('avatar')} className={`px-3 py-2 rounded-lg text-sm border ${videoSourceType === 'avatar' ? 'bg-primary/10 border-primary/40 text-primary' : 'border-border-default text-text-secondary'}`}>{t('mediaAi.fromAvatar')}</button>
            </div>
            {videoSourceType === 'upload' ? (
              <input type="file" accept="video/*" onChange={(e) => setVideoFile(e.target.files?.[0] || null)} className="mt-2 w-full text-sm" />
            ) : videoSourceType === 'url' ? (
              <input value={videoUrlInput} onChange={(e) => setVideoUrlInput(e.target.value)} className="mt-2 w-full bg-bg-tertiary border border-border-default rounded-lg px-3 py-2 text-sm" placeholder={t('mediaAi.videoUrlPlaceholder')} />
            ) : (
              <select value={selectedAvatarId} onChange={(e) => setSelectedAvatarId(e.target.value)} className="mt-2 w-full bg-bg-tertiary border border-border-default rounded-lg px-3 py-2 text-sm">
                <option value="">{t('mediaAi.selectAvatar')}</option>
                {avatars.map((avatar) => (
                  <option key={avatar.id} value={avatar.id}>{avatar.title || avatar.avatarId || 'Avatar'}</option>
                ))}
              </select>
            )}
          </div>

          <div>
            <label className="text-sm font-medium text-text-secondary">{t('mediaAi.audioSource')}</label>
            <div className="mt-2 flex flex-wrap gap-2">
              <button onClick={() => setAudioSourceType('upload')} className={`px-3 py-2 rounded-lg text-sm border ${audioSourceType === 'upload' ? 'bg-primary/10 border-primary/40 text-primary' : 'border-border-default text-text-secondary'}`}>{t('mediaAi.uploadAudio')}</button>
              <button onClick={() => setAudioSourceType('tts')} className={`px-3 py-2 rounded-lg text-sm border ${audioSourceType === 'tts' ? 'bg-primary/10 border-primary/40 text-primary' : 'border-border-default text-text-secondary'}`}>{t('mediaAi.fromTts')}</button>
              <button onClick={() => setAudioSourceType('script')} className={`px-3 py-2 rounded-lg text-sm border ${audioSourceType === 'script' ? 'bg-primary/10 border-primary/40 text-primary' : 'border-border-default text-text-secondary'}`}>{t('mediaAi.fromScript')}</button>
            </div>
          </div>

          {audioSourceType === 'upload' && (
            <input type="file" accept="audio/*" onChange={(e) => setAudioFile(e.target.files?.[0] || null)} className="w-full text-sm" />
          )}

          {audioSourceType === 'tts' && (
            <select value={selectedSpeechId} onChange={(e) => setSelectedSpeechId(e.target.value)} className="w-full bg-bg-tertiary border border-border-default rounded-lg px-3 py-2 text-sm">
              <option value="">{t('mediaAi.selectSpeech')}</option>
              {speeches.map((speech) => (
                <option key={speech.id} value={speech.id}>{speech.voiceName} - {speech.text.slice(0, 24)}...</option>
              ))}
            </select>
          )}

          {audioSourceType === 'script' && (
            <div className="space-y-3">
              <select value={scriptVoiceId} onChange={(e) => setScriptVoiceId(e.target.value)} className="w-full bg-bg-tertiary border border-border-default rounded-lg px-3 py-2 text-sm">
                <option value="">{t('mediaAi.selectVoicePlaceholder')}</option>
                {voices.map((voice) => (
                  <option key={voice.voiceId} value={voice.voiceId}>{voice.title || voice.voiceId}</option>
                ))}
              </select>
              <div>
                <label className="text-sm font-medium text-text-secondary">{t('mediaAi.ttsSpeed')}</label>
                <div className="mt-2 flex items-center gap-3">
                  <input
                    type="range"
                    min="0.5"
                    max="2"
                    step="0.05"
                    value={scriptTtsSpeed}
                    onChange={(e) => setScriptTtsSpeed(Number(e.target.value))}
                    className="w-full"
                  />
                  <input
                    type="number"
                    min="0.5"
                    max="2"
                    step="0.05"
                    value={scriptTtsSpeed}
                    onChange={(e) => {
                      const next = Number(e.target.value);
                      if (!Number.isFinite(next)) return;
                      setScriptTtsSpeed(Math.max(0.5, Math.min(2, next)));
                    }}
                    className="w-24 bg-bg-tertiary border border-border-default rounded-lg px-2 py-1 text-sm"
                  />
                </div>
              </div>
              <textarea value={scriptText} onChange={(e) => setScriptText(e.target.value)} className="w-full bg-bg-tertiary border border-border-default rounded-lg px-3 py-2 text-sm min-h-[120px]" placeholder={t('mediaAi.scriptPlaceholder')} />
              <TTSTagControls
                emotionTag={scriptEmotionTag}
                toneTags={scriptToneTags}
                effectTags={scriptEffectTags}
                onEmotionChange={setScriptEmotionTag}
                onToneTagsChange={setScriptToneTags}
                onEffectTagsChange={setScriptEffectTags}
              />
              <div className="border border-border-default rounded-lg p-3 space-y-2">
                <label className="flex items-center gap-2 text-xs text-text-muted">
                  <input type="checkbox" checked={scriptUseVoiceProfile} onChange={(e) => setScriptUseVoiceProfile(e.target.checked)} />
                  {t('mediaAi.useVoiceProfile')}
                </label>
                <label className="flex items-center gap-2 text-xs text-text-muted">
                  <input type="checkbox" checked={scriptAutoEmotion} onChange={(e) => setScriptAutoEmotion(e.target.checked)} />
                  {t('mediaAi.autoSentenceEmotion')}
                </label>
                <label className="flex items-center gap-2 text-xs text-text-muted">
                  <input type="checkbox" checked={scriptAutoBreaks} onChange={(e) => setScriptAutoBreaks(e.target.checked)} />
                  {t('mediaAi.autoSentenceBreaks')}
                </label>
              </div>
            </div>
          )}

          <div>
            <label className="text-sm font-medium text-text-secondary">Model</label>
            <select value={model} onChange={(e) => setModel(e.target.value)} className="mt-2 w-full bg-bg-tertiary border border-border-default rounded-lg px-3 py-2 text-sm">
              <option value="lipsync-2">lipsync-2</option>
              <option value="lipsync-1.9.0-beta">lipsync-1.9.0-beta</option>
              <option value="lipsync-2-pro">lipsync-2-pro</option>
            </select>
          </div>

          {error && <p className="text-sm text-red-400">{error}</p>}

          <button
            onClick={handleGenerate}
            disabled={!canGenerate || loading}
            className="w-full px-4 py-2 rounded-lg bg-primary text-white disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? t('mediaAi.processing') : t('mediaAi.generateLipsync')}
          </button>
        </div>

        <div className="border border-border-default rounded-xl p-4">
          <h4 className="font-medium text-text-primary mb-3">{t('mediaAi.recentGenerations')}</h4>
          <input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={t('mediaAi.searchPlaceholder')}
            className="mb-3 w-full bg-bg-tertiary border border-border-default rounded-lg px-3 py-2 text-sm"
          />
          <div className="space-y-3 max-h-[520px] overflow-y-auto custom-scrollbar pr-1">
            {filteredGenerations.length === 0 && <p className="text-sm text-text-muted">{t('mediaAi.noGenerations')}</p>}
            {filteredGenerations.map((item) => (
              <div key={item.id} className="border border-border-default rounded-lg p-3">
                <div className="flex items-center justify-between gap-2">
                  <p className="font-medium text-sm text-text-primary">{item.model}</p>
                  <span className="text-xs text-text-muted">{item.status}</span>
                </div>
                <p className="text-xs text-text-muted mt-1">{item.generationId}</p>
                {item.outputUrl ? (
                  <video className="w-full mt-2 rounded" controls preload="metadata" src={toPlayableMediaUrl(item.outputUrl)} />
                ) : (
                  <p className="text-xs text-text-muted mt-2">{t('mediaAi.processingStatus')}</p>
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

export default LipsyncManager;
