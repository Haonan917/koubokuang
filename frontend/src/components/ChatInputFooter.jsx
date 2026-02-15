import React, { useState, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import ModeSelector from './ModeSelector';
import { DEFAULT_MODE } from '../constants/modes';
import { ensureChatPreferences, readChatPreferences, writeChatPreferences } from '../utils/chatPreferences';
import { fetchMediaAiAvatars, fetchMediaAiVoices } from '../services/api';
import { normalizeAvatarItem, normalizeVoiceItem, toPlayableMediaUrl } from '../utils/mediaUrl';
import { LLM_MODEL_OPTIONS } from '../constants/llmModels';

/**
 * ChatInputFooter - 底部统一输入组件
 *
 * 支持：
 * 1. 自由对话（无需链接）
 * 2. 链接分析（自动检测 URL + 模式选择）
 * 3. 智能切换（有会话后隐藏模式选择器）
 */
function ChatInputFooter({ onSend, onAnalyze, onStop, loading, sessionId }) {
  const { t } = useTranslation();
  const [inputValue, setInputValue] = useState('');
  const [selectedMode, setSelectedMode] = useState(DEFAULT_MODE);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [detectedUrl, setDetectedUrl] = useState(null);
  const textareaRef = useRef(null);
  const [voiceOptions, setVoiceOptions] = useState([]);
  const [avatarOptions, setAvatarOptions] = useState([]);
  const [selectedVoiceId, setSelectedVoiceId] = useState('');
  const [selectedAvatarId, setSelectedAvatarId] = useState('');
  const [selectedModelName, setSelectedModelName] = useState('');
  const selectedVoice = voiceOptions.find((v) => v.voiceId === selectedVoiceId) || null;
  const selectedAvatar = avatarOptions.find((a) => (a.avatarId || String(a.id || '')) === selectedAvatarId) || null;

  // 自动调整 textarea 高度
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
    }
  }, [inputValue]);

  const refreshPreferences = async () => {
    const applyPreferences = () => {
      const { voices, avatars, voiceId, avatarId, modelName } = ensureChatPreferences();
      setVoiceOptions(voices);
      setAvatarOptions(avatars);
      setSelectedVoiceId(voiceId || '');
      setSelectedAvatarId(avatarId || '');
      setSelectedModelName(modelName || '');
    };

    applyPreferences();

    try {
      const [voicesRes, avatarsRes] = await Promise.all([
        fetchMediaAiVoices(),
        fetchMediaAiAvatars(),
      ]);
      const remoteVoices = Array.isArray(voicesRes?.data) ? voicesRes.data.map((item) => normalizeVoiceItem(item)) : [];
      const remoteAvatars = Array.isArray(avatarsRes?.data) ? avatarsRes.data.map((item) => normalizeAvatarItem(item)) : [];
      if (remoteVoices.length > 0) {
        const merged = [...remoteVoices, ...voiceOptions].filter(Boolean);
        localStorage.setItem('media_ai_voices', JSON.stringify(merged));
      }
      if (remoteAvatars.length > 0) {
        const merged = [...remoteAvatars, ...avatarOptions].filter(Boolean);
        localStorage.setItem('media_ai_avatars', JSON.stringify(merged));
      }
      applyPreferences();
    } catch {
      // ignore
    }
  };

  useEffect(() => {
    refreshPreferences();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  // 从输入内容中提取 URL
  const extractUrl = (text) => {
    const urlMatch = text.match(/https?:\/\/[^\s]+/);
    return urlMatch ? urlMatch[0] : null;
  };

  // 自动检测 URL
  useEffect(() => {
    const url = extractUrl(inputValue);
    setDetectedUrl(url);
  }, [inputValue]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!inputValue.trim() || loading) return;

    const url = extractUrl(inputValue);
    if (url && !sessionId) {
      // 有 URL 且无会话 → 调用分析
      onAnalyze(inputValue.trim(), selectedMode.id);
    } else {
      // 无 URL 或有会话 → 调用对话
      onSend(inputValue.trim());
    }
    setInputValue('');
  };

  const handleButtonClick = (e) => {
    e.preventDefault();

    if (loading) {
      // Loading 时点击 = 停止生成
      onStop?.();
    } else {
      // 否则发送消息
      if (!inputValue.trim()) return;

      const url = extractUrl(inputValue);
      if (url && !sessionId) {
        onAnalyze(inputValue.trim(), selectedMode.id);
      } else {
        onSend(inputValue.trim());
      }
      setInputValue('');
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleSelectMode = (mode) => {
    setSelectedMode(mode);
    // 预填充提示词（可选）
    const prefill = t(`${mode.i18nKey}.prefill`);
    setInputValue(`${prefill}：`);
    // 聚焦输入框并定位光标到末尾
    setTimeout(() => {
      if (textareaRef.current) {
        textareaRef.current.focus();
        const len = textareaRef.current.value.length;
        textareaRef.current.setSelectionRange(len, len);
      }
    }, 0);
  };

  // 判断是否显示模式选择器（无会话时显示）
  const showModeSelector = !sessionId;

  // 判断发送按钮图标
  const isAnalyzeMode = detectedUrl && !sessionId;

  // 动态 placeholder
  const placeholder = detectedUrl && !sessionId
    ? t('chatFooter.placeholderWithUrl', { defaultValue: '已检测到链接，选择分析模式后点击发送' })
    : t('chatFooter.placeholder', { defaultValue: '随时开始对话，或粘贴链接进行分析...' });

  return (
    <footer className="chat-input-footer">
      <div className="max-w-4xl mx-auto w-full px-8 flex flex-col gap-4">
        <div className="flex flex-wrap items-center gap-4 text-xs text-text-muted">
          <div className="flex items-center gap-2">
            <span className="text-text-secondary">LLM</span>
            <select
              value={selectedModelName}
              onChange={(e) => {
                const next = e.target.value;
                setSelectedModelName(next);
                const pref = readChatPreferences();
                writeChatPreferences({ voiceId: pref.voiceId, avatarId: pref.avatarId, modelName: next });
              }}
              className="bg-bg-secondary border border-border-default rounded-md px-2 py-1 text-xs"
              disabled={LLM_MODEL_OPTIONS.length === 0}
            >
              {LLM_MODEL_OPTIONS.map((model) => (
                <option key={model.value} value={model.value}>
                  {model.label}
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-text-secondary">{t('mediaAi.chatVoiceLabel')}</span>
            <select
              value={selectedVoiceId}
              onChange={(e) => {
                const next = e.target.value;
                setSelectedVoiceId(next);
                const pref = readChatPreferences();
                writeChatPreferences({ voiceId: next, avatarId: pref.avatarId, modelName: pref.modelName });
              }}
              onFocus={refreshPreferences}
              className="bg-bg-secondary border border-border-default rounded-md px-2 py-1 text-xs"
              disabled={voiceOptions.length === 0}
            >
              <option value="">{t('mediaAi.selectVoicePlaceholder')}</option>
              {voiceOptions.map((voice) => (
                <option key={voice.voiceId} value={voice.voiceId}>
                  {voice.title || voice.voiceId}
                </option>
              ))}
            </select>
            {voiceOptions.length > 0 ? (
              <button
                type="button"
                onClick={() => {
                  const next = voiceOptions[0]?.voiceId || '';
                  if (!next) return;
                  setSelectedVoiceId(next);
                  const pref = readChatPreferences();
                  writeChatPreferences({ voiceId: next, avatarId: pref.avatarId, modelName: pref.modelName });
                }}
                className="px-2 py-1 rounded-md border border-border-default"
              >
                {t('mediaAi.useRecentVoice')}
              </button>
            ) : (
              <span className="text-text-muted">{t('mediaAi.noVoices')}</span>
            )}
          </div>

          <div className="flex items-center gap-2">
            <span className="text-text-secondary">{t('mediaAi.chatAvatarLabel')}</span>
            <select
              value={selectedAvatarId}
              onChange={(e) => {
                const next = e.target.value;
                setSelectedAvatarId(next);
                const pref = readChatPreferences();
                writeChatPreferences({ voiceId: pref.voiceId, avatarId: next, modelName: pref.modelName });
              }}
              onFocus={refreshPreferences}
              className="bg-bg-secondary border border-border-default rounded-md px-2 py-1 text-xs"
              disabled={avatarOptions.length === 0}
            >
              <option value="">{t('mediaAi.selectAvatar')}</option>
              {avatarOptions.map((avatar) => (
                <option key={avatar.avatarId || avatar.id} value={avatar.avatarId || avatar.id}>
                  {avatar.title || avatar.avatarId || avatar.id}
                </option>
              ))}
            </select>
            {avatarOptions.length > 0 ? (
              <button
                type="button"
                onClick={() => {
                  const next = avatarOptions[0]?.avatarId || avatarOptions[0]?.id || '';
                  if (!next) return;
                  setSelectedAvatarId(String(next));
                  const pref = readChatPreferences();
                  writeChatPreferences({ voiceId: pref.voiceId, avatarId: String(next), modelName: pref.modelName });
                }}
                className="px-2 py-1 rounded-md border border-border-default"
              >
                {t('mediaAi.useRecentAvatar')}
              </button>
            ) : (
              <span className="text-text-muted">{t('mediaAi.noAvatars')}</span>
            )}
          </div>
        </div>

        <div className="flex flex-wrap gap-3 text-xs text-text-muted">
          <div className="flex items-center gap-3 border border-border-default rounded-lg px-3 py-2 bg-bg-secondary/60">
            <span className="text-text-secondary">{t('mediaAi.chatVoicePreview')}</span>
            {selectedVoice?.clipAudioUrl || selectedVoice?.sampleAudioUrl || selectedVoice?.fullAudioUrl ? (
              <audio
                className="h-8"
                controls
                preload="metadata"
                src={toPlayableMediaUrl(selectedVoice.clipAudioUrl || selectedVoice.sampleAudioUrl || selectedVoice.fullAudioUrl)}
              />
            ) : (
              <span className="text-text-muted">{t('mediaAi.noVoicePreview')}</span>
            )}
          </div>
          <div className="flex items-center gap-3 border border-border-default rounded-lg px-3 py-2 bg-bg-secondary/60">
            <span className="text-text-secondary">{t('mediaAi.chatAvatarPreview')}</span>
            {selectedAvatar?.clipVideoUrl || selectedAvatar?.fullVideoUrl || selectedAvatar?.sourceUrl ? (
              <video
                className="h-12 rounded"
                controls
                preload="metadata"
                src={toPlayableMediaUrl(selectedAvatar.clipVideoUrl || selectedAvatar.fullVideoUrl || selectedAvatar.sourceUrl)}
              />
            ) : (
              <span className="text-text-muted">{t('mediaAi.noAvatarPreview')}</span>
            )}
          </div>
        </div>

        {/* Chat Input */}
        <div className="chat-input-wrapper">
          {/* Glow effect on focus */}
          <div className="glow" />

          <div className="chat-input-container">
            {/* 模式选择器（仅在无会话时显示）*/}
            {showModeSelector && (
              <ModeSelector
                selectedMode={selectedMode}
                onSelectMode={handleSelectMode}
                isOpen={isDropdownOpen}
                onToggle={() => setIsDropdownOpen(!isDropdownOpen)}
              />
            )}

            {/* AI Icon（有会话时显示）*/}
            {!showModeSelector && (
              <div className="chat-input-icon">
                <span className="material-symbols-outlined">
                  auto_fix_high
                </span>
              </div>
            )}

            {/* Input field */}
            <textarea
              ref={textareaRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={placeholder}
              className="chat-input-field"
              disabled={loading}
              rows={1}
            />

            {/* Send/Stop button */}
            <button
              onClick={handleButtonClick}
              disabled={!loading && !inputValue.trim()}
              className={`chat-send-button ${isAnalyzeMode ? 'url-detected' : ''} ${loading ? 'stop-mode' : ''}`}
              title={loading ? t('chatFooter.stop') : (isAnalyzeMode ? t('chatFooter.startAnalysis') : t('chatFooter.send'))}
            >
              <span className="material-symbols-outlined">
                {loading ? 'stop_circle' : (isAnalyzeMode ? 'auto_awesome' : 'send')}
              </span>
            </button>
          </div>
        </div>

        {/* Keyboard hint */}
        <p className="chat-input-hint">
          {t('chatFooter.pressHint')} <kbd>Enter</kbd> {t('chatFooter.enterToSend')} • <kbd>Shift + Enter</kbd> {t('chatFooter.shiftEnterNewLine')}
        </p>
      </div>
    </footer>
  );
}

export default ChatInputFooter;
