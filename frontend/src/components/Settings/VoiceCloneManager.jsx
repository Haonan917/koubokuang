import React, { useMemo, useRef, useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { cloneVoice, uploadAudioFile, fetchMediaAiVoices } from '../../services/api';
import { normalizeMediaUrl, normalizeVoiceItem, toPlayableMediaUrl } from '../../utils/mediaUrl';
import { readChatPreferences, writeChatPreferences } from '../../utils/chatPreferences';

const VOICES_STORAGE_KEY = 'media_ai_voices';

function readVoices() {
  try {
    const raw = localStorage.getItem(VOICES_STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed.map((item) => normalizeVoiceItem(item)) : [];
  } catch {
    return [];
  }
}

function writeVoices(voices) {
  localStorage.setItem(VOICES_STORAGE_KEY, JSON.stringify(voices));
}

function mergeVoices(localList, remoteList) {
  const map = new Map();
  for (const item of [...remoteList, ...localList]) {
    const voiceId = item.voiceId || item.voice_id || '';
    const key = voiceId || item.sampleAudioUrl || item.fullAudioUrl || item.clipAudioUrl;
    if (!key) continue;
    const prev = map.get(key) || {};
    map.set(key, { ...prev, ...item, voiceId: voiceId || prev.voiceId });
  }
  return Array.from(map.values());
}

function VoiceCloneManager() {
  const { t } = useTranslation();
  const fileInputRef = useRef(null);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [sourceType, setSourceType] = useState('upload'); // upload | recording | content_video
  const [audioFile, setAudioFile] = useState(null);
  const [videoUrl, setVideoUrl] = useState('');
  const [startSeconds, setStartSeconds] = useState(0);
  const [durationSeconds, setDurationSeconds] = useState(30);
  const [voices, setVoices] = useState(() => readVoices());
  const [searchQuery, setSearchQuery] = useState('');
  const [serverOffset, setServerOffset] = useState(0);
  const [serverTotal, setServerTotal] = useState(0);
  const [serverLoading, setServerLoading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const mediaRecorderRef = useRef(null);
  const recordingTimerRef = useRef(null);
  const recordingChunksRef = useRef([]);

  const canSubmit = useMemo(() => {
    if (sourceType === 'content_video') return videoUrl.trim().length > 0;
    return !!audioFile;
  }, [sourceType, audioFile, videoUrl]);

  const filteredVoices = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return voices;
    return voices.filter((voice) => {
      const hay = [
        voice.title,
        voice.description,
        voice.voiceId,
        voice.sourceType,
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();
      return hay.includes(q);
    });
  }, [voices, searchQuery]);

  const persistVoices = (nextVoices) => {
    setVoices(nextVoices);
    writeVoices(nextVoices);
  };

  const loadFromServer = async (nextOffset = 0, queryText = '') => {
    setServerLoading(true);
    try {
      const response = await fetchMediaAiVoices(20, nextOffset, queryText);
      const remote = Array.isArray(response?.data) ? response.data.map((item) => normalizeVoiceItem(item)) : [];
      const merged = mergeVoices(voices, remote);
      persistVoices(merged);
      setServerOffset(nextOffset + remote.length);
      setServerTotal(Number(response?.total || 0));
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

  const handlePickAudio = () => {
    fileInputRef.current?.click();
  };

  const handleAudioChange = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setAudioFile(file);
    setError('');
  };

  const stopRecordingTimer = () => {
    if (recordingTimerRef.current) {
      clearInterval(recordingTimerRef.current);
      recordingTimerRef.current = null;
    }
  };

  const startRecording = async () => {
    if (!window.isSecureContext && !window.location.hostname.includes('localhost')) {
      throw new Error(t('mediaAi.recordingSecureContext'));
    }
    if (!navigator?.mediaDevices?.getUserMedia) {
      throw new Error(t('mediaAi.recordingUnsupported'));
    }
    if (typeof MediaRecorder === 'undefined') {
      throw new Error(t('mediaAi.recordingUnsupported'));
    }

    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const mimeCandidates = [
      'audio/webm;codecs=opus',
      'audio/webm',
      'audio/mp4',
      'audio/ogg;codecs=opus',
      'audio/wav',
    ];
    const chosenMime = mimeCandidates.find((m) => MediaRecorder.isTypeSupported?.(m)) || '';
    const recorder = chosenMime ? new MediaRecorder(stream, { mimeType: chosenMime }) : new MediaRecorder(stream);
    recordingChunksRef.current = [];
    setAudioFile(null);

    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) recordingChunksRef.current.push(event.data);
    };

    recorder.onstop = () => {
      const finalMime = chosenMime || recorder.mimeType || 'audio/webm';
      const ext = finalMime.includes('mp4') ? 'mp4' : finalMime.includes('ogg') ? 'ogg' : finalMime.includes('wav') ? 'wav' : 'webm';
      const blob = new Blob(recordingChunksRef.current, { type: finalMime });
      const file = new File([blob], `recording_${Date.now()}.${ext}`, { type: finalMime });
      setAudioFile(file);
      stream.getTracks().forEach((track) => track.stop());
    };

    recorder.start();
    mediaRecorderRef.current = recorder;
    setIsRecording(true);
    setRecordingTime(0);
    recordingTimerRef.current = setInterval(() => setRecordingTime((s) => s + 1), 1000);
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
    mediaRecorderRef.current = null;
    setIsRecording(false);
    stopRecordingTimer();
  };

  const handleRecordToggle = async () => {
    setError('');
    try {
      if (isRecording) {
        stopRecording();
      } else {
        await startRecording();
      }
    } catch (e) {
      setError(e.message || 'Failed to access microphone');
      setIsRecording(false);
      stopRecordingTimer();
    }
  };

  const formatTime = (seconds) => {
    const m = Math.floor(seconds / 60);
    const s = String(seconds % 60).padStart(2, '0');
    return `${m}:${s}`;
  };

  const handleCloneVoice = async () => {
    if (!canSubmit || loading) return;
    setLoading(true);
    setError('');
    try {
      let sourceUrl = videoUrl.trim();

      if (sourceType !== 'content_video') {
        const uploadResult = await uploadAudioFile(audioFile);
        sourceUrl = uploadResult?.data?.url || '';
      }

      const result = await cloneVoice({
        sourceType,
        sourceUrl,
        title: title || 'Untitled',
        description,
        startSeconds,
        durationSeconds,
      });

      const item = {
        id: Date.now(),
        title: result?.data?.title || title || 'Untitled',
        description: result?.data?.description || description,
        sourceType: result?.data?.sourceType || sourceType,
        voiceId: result?.data?.voiceId,
        sampleAudioUrl: normalizeMediaUrl(result?.data?.sampleAudioUrl),
        fullAudioUrl: normalizeMediaUrl(result?.data?.fullAudioUrl),
        clipAudioUrl: normalizeMediaUrl(result?.data?.clipAudioUrl),
        sourceUrl: normalizeMediaUrl(sourceUrl),
        expressionProfile: result?.data?.expressionProfile,
        timestamp: new Date().toLocaleString(),
      };
      const nextVoices = [item, ...voices];
      persistVoices(nextVoices);
      const chatPref = readChatPreferences();
      if (!chatPref.voiceId) {
        writeChatPreferences({ voiceId: item.voiceId, avatarId: chatPref.avatarId });
      }

      setTitle('');
      setDescription('');
      setAudioFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
    } catch (e) {
      setError(e.message || 'Clone voice failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-xl font-semibold text-text-primary">{t('mediaAi.voiceCloneTitle')}</h3>
        <p className="text-sm text-text-muted mt-1">{t('mediaAi.voiceCloneDesc')}</p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div className="border border-border-default rounded-xl p-4 space-y-4">
          <div>
            <label className="text-sm font-medium text-text-secondary">{t('mediaAi.title')}</label>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="mt-2 w-full bg-bg-tertiary border border-border-default rounded-lg px-3 py-2 text-sm"
              placeholder={t('mediaAi.titlePlaceholder')}
            />
          </div>

          <div>
            <label className="text-sm font-medium text-text-secondary">{t('mediaAi.description')}</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="mt-2 w-full bg-bg-tertiary border border-border-default rounded-lg px-3 py-2 text-sm min-h-[96px]"
              placeholder={t('mediaAi.descriptionPlaceholder')}
            />
          </div>

          <div>
            <label className="text-sm font-medium text-text-secondary">{t('mediaAi.sourceType')}</label>
            <div className="mt-2 flex flex-wrap gap-2">
              <button onClick={() => { setSourceType('upload'); setIsRecording(false); stopRecordingTimer(); }} className={`px-3 py-2 rounded-lg text-sm border ${sourceType === 'upload' ? 'bg-primary/10 border-primary/40 text-primary' : 'border-border-default text-text-secondary'}`}>{t('mediaAi.sourceUpload')}</button>
              <button onClick={() => setSourceType('recording')} className={`px-3 py-2 rounded-lg text-sm border ${sourceType === 'recording' ? 'bg-primary/10 border-primary/40 text-primary' : 'border-border-default text-text-secondary'}`}>{t('mediaAi.sourceRecording')}</button>
              <button onClick={() => setSourceType('content_video')} className={`px-3 py-2 rounded-lg text-sm border ${sourceType === 'content_video' ? 'bg-primary/10 border-primary/40 text-primary' : 'border-border-default text-text-secondary'}`}>{t('mediaAi.sourceVideo30s')}</button>
            </div>
          </div>

          {sourceType === 'content_video' ? (
            <div className="space-y-3">
              <input
                value={videoUrl}
                onChange={(e) => setVideoUrl(e.target.value)}
                className="w-full bg-bg-tertiary border border-border-default rounded-lg px-3 py-2 text-sm"
                placeholder={t('mediaAi.videoUrlPlaceholder')}
              />
              <div className="grid grid-cols-2 gap-3">
                <input
                  type="number"
                  min="0"
                  value={startSeconds}
                  onChange={(e) => setStartSeconds(Number(e.target.value || 0))}
                  className="bg-bg-tertiary border border-border-default rounded-lg px-3 py-2 text-sm"
                  placeholder="start(s)"
                />
                <input
                  type="number"
                  min="1"
                  value={durationSeconds}
                  onChange={(e) => setDurationSeconds(Number(e.target.value || 30))}
                  className="bg-bg-tertiary border border-border-default rounded-lg px-3 py-2 text-sm"
                  placeholder="duration(s)"
                />
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              <input ref={fileInputRef} type="file" accept="audio/*" onChange={handleAudioChange} className="hidden" />
              <div className="flex flex-wrap gap-2">
                <button onClick={handlePickAudio} className="px-3 py-2 rounded-lg text-sm border border-border-default hover:border-primary/50">
                  {t('mediaAi.uploadAudio')}
                </button>
                {sourceType === 'recording' && (
                  <button onClick={handleRecordToggle} className={`px-3 py-2 rounded-lg text-sm border ${isRecording ? 'border-red-400 text-red-400' : 'border-border-default'}`}>
                    {isRecording ? t('mediaAi.stopRecording') : t('mediaAi.startRecording')}
                  </button>
                )}
              </div>
              {isRecording && <p className="text-xs text-text-muted">{t('mediaAi.recording')}: {formatTime(recordingTime)}</p>}
              {audioFile && <p className="text-xs text-text-muted">✅ {audioFile.name}</p>}
            </div>
          )}

          {error && <p className="text-sm text-red-400">{error}</p>}

          <button
            onClick={handleCloneVoice}
            disabled={!canSubmit || loading}
            className="w-full px-4 py-2 rounded-lg bg-primary text-white disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? t('mediaAi.processing') : t('mediaAi.cloneVoice')}
          </button>
        </div>

        <div className="border border-border-default rounded-xl p-4">
          <h4 className="font-medium text-text-primary mb-3">{t('mediaAi.recentVoices')}</h4>
          <input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={t('mediaAi.searchPlaceholder')}
            className="mb-3 w-full bg-bg-tertiary border border-border-default rounded-lg px-3 py-2 text-sm"
          />
          <div className="space-y-3 max-h-[520px] overflow-y-auto custom-scrollbar pr-1">
            {filteredVoices.length === 0 && (
              <p className="text-sm text-text-muted">{t('mediaAi.noVoices')}</p>
            )}
            {filteredVoices.map((voice) => (
              <div key={voice.id} className="border border-border-default rounded-lg p-3">
                <div className="flex items-center justify-between gap-2">
                  <p className="font-medium text-sm text-text-primary">{voice.title || 'Untitled'}</p>
                  <span className="text-xs text-text-muted">{voice.sourceType}</span>
                </div>
                <p className="text-xs text-text-muted mt-1">{voice.description || '-'}</p>
                <p className="text-[11px] text-text-muted mt-1">{voice.voiceId}</p>
                {voice.expressionProfile && (
                  <>
                    <p className="text-[11px] text-text-muted mt-1">
                      autoEmotion: {String(Boolean(voice.expressionProfile.auto_emotion))} · autoBreaks: {String(Boolean(voice.expressionProfile.auto_breaks))}
                    </p>
                    <p className="text-[11px] text-text-muted mt-1">
                      {[
                        ...(voice.expressionProfile.tone_tags || []),
                        ...(voice.expressionProfile.effect_tags || []),
                      ].join(' ') || '-'}
                    </p>
                  </>
                )}
                {voice.fullAudioUrl && (
                  <div className="mt-2">
                    <p className="text-[11px] text-text-muted mb-1">{t('mediaAi.fullAudio')}</p>
                    <audio className="w-full" controls preload="metadata" src={toPlayableMediaUrl(voice.fullAudioUrl)} />
                  </div>
                )}
                {voice.clipAudioUrl && (
                  <div className="mt-2">
                    <p className="text-[11px] text-text-muted mb-1">{t('mediaAi.clipAudio')}</p>
                    <audio className="w-full" controls preload="metadata" src={toPlayableMediaUrl(voice.clipAudioUrl)} />
                  </div>
                )}
                {voice.sampleAudioUrl && (
                  <div className="mt-2">
                    <p className="text-[11px] text-text-muted mb-1">{t('mediaAi.sampleAudio')}</p>
                    <audio className="w-full" controls preload="metadata" src={toPlayableMediaUrl(voice.sampleAudioUrl)} />
                  </div>
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

export default VoiceCloneManager;
