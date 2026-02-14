import React, { memo, useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import StepsCollapsible from './StepsCollapsible';
import MarkdownBlock from './MarkdownBlock';
import ContentCard from './ContentCard';
import TranscriptCard from './TranscriptCard';
import MessageActions from './MessageActions';
import { normalizeMediaUrl, toPlayableMediaUrl } from '../utils/mediaUrl';
import { extractChatMediaResults, persistChatMediaResults } from '../utils/chatMediaResults';
import { textToSpeech } from '../services/api';
import { ADVANCED_EMOTION_TAGS, BASIC_EMOTION_TAGS, EFFECT_TAGS, TONE_TAGS } from '../utils/ttsTags';
import {
  userMessageToMarkdown,
  aiMessageToMarkdown,
  copyToClipboard,
} from '../utils/copyToMarkdown';

/**
 * MessageItem - 消息项组件
 *
 * 深色主题风格的消息渲染
 * 用户消息：青色气泡，右对齐
 * AI消息：左对齐，包含头像、步骤列表、内容卡片、底部操作栏
 */
export function MessageItem({ message, onRetry }) {
  const isUser = message.role === 'user';
  const isStreaming = message.isComplete === false;

  // 使用 segments 数组
  const segments = message.segments || [];

  // 提取结构化数据
  const structuredData = message.structuredData;

  if (isUser) {
    return <UserMessage content={message.content} />;
  }

  return (
    <AIMessage
      segments={segments}
      structuredData={structuredData}
      isStreaming={isStreaming}
      onRetry={onRetry}
    />
  );
}

/**
 * 用户消息组件
 *
 * 直接显示用户原始输入内容，不做任何处理
 * hover 时显示复制按钮
 */
const UserMessage = memo(function UserMessage({ content }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async (e) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      const success = await copyToClipboard(content);
      if (success) {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      }
    } catch (err) {
      console.error('Copy failed:', err);
    }
  }, [content]);

  return (
    <div className="flex flex-col items-end mb-8 animate-fade-in group">
      {/* 消息气泡 */}
      <div className="max-w-[85%] bg-gradient-to-br from-primary to-primary-active text-white px-6 py-4 rounded-2xl rounded-tr-none shadow-[0_4px_20px_rgba(255,59,59,0.25)]">
        <div className="text-sm leading-relaxed whitespace-pre-wrap break-all">
          {content}
        </div>
      </div>
      {/* 复制按钮 - 右下角，hover 时显示 */}
      <button
        onClick={handleCopy}
        className={`user-message-copy-btn ${copied ? 'copied' : ''}`}
        title={copied ? '已复制' : '复制'}
      >
        <span className="material-symbols-outlined">
          {copied ? 'check' : 'content_copy'}
        </span>
      </button>
    </div>
  );
});

/**
 * AI 消息组件
 *
 * 完成后在底部显示操作栏（复制、重试）
 */
const AIMessage = memo(function AIMessage({ segments, structuredData, isStreaming, onRetry }) {
  const { t } = useTranslation();

  // 简化：直接根据 segment type 分类，不再需要复杂的顺序判断
  // 后端通过 final_report_start 事件已正确标记了 process_text 和 markdown
  const stepSegments = segments.filter(
    s => s.type === 'intent' ||
         s.type === 'tool_call' ||
         s.type === 'thinking' ||
         s.type === 'sub_step' ||
         s.type === 'process_text'  // 后端已正确标记
  );

  const contentSegments = segments.filter(
    s => s.type === 'text' || s.type === 'markdown'  // 只有最终报告
  );

  const mediaResults = useMemo(
    () => extractChatMediaResults(segments, structuredData),
    [segments, structuredData]
  );
  const hasMediaResults = mediaResults.voices.length > 0 || mediaResults.speeches.length > 0 || mediaResults.generations.length > 0;

  // 获取 content_info segment
  const contentInfoSegment = segments.find(s => s.type === 'content_info');
  const contentInfo = contentInfoSegment?.data;

  // 获取 transcript（从多个来源尝试获取）
  // 后端返回 TranscriptResult: { text: string, segments: [{start, end, text}, ...] }
  // 优先级: transcript segment > contentInfo > structuredData (done 事件)
  const transcriptSegment = segments.find(s => s.type === 'transcript');
  const transcriptData =
    transcriptSegment?.data ||
    transcriptSegment?.content ||
    contentInfo?.transcript ||
    structuredData?.transcript;  // 从 done 事件的 structuredData 获取

  // 提取 segments 数组（如果存在）
  const transcriptSegments = transcriptData?.segments || null;
  const transcript = transcriptData?.text || (typeof transcriptData === 'string' ? transcriptData : null);

  // 检查是否有内容显示
  const hasSteps = stepSegments.length > 0;
  const hasContent = contentSegments.length > 0 || contentInfo;
  const hasAnyContent = hasSteps || hasContent || hasMediaResults;

  // 是否显示报告头部（第一个 markdown segment）
  const showReportHeader = contentSegments.length > 0 && contentSegments[0].type === 'markdown';

  // 复制为 Markdown 的回调
  const getMarkdown = useCallback(
    () => aiMessageToMarkdown(segments, structuredData),
    [segments, structuredData]
  );

  useEffect(() => {
    if (!isStreaming && hasMediaResults) {
      persistChatMediaResults(mediaResults);
    }
  }, [isStreaming, hasMediaResults, mediaResults]);

  return (
    <div className="flex flex-col gap-8 animate-fade-in">
      {/* 步骤列表（可折叠） - Analysis Complete 卡片 */}
      {hasSteps && (
        <StepsCollapsible steps={stepSegments} isStreaming={isStreaming} />
      )}

      {/* 内容卡片 - ContentCard（根据类型展示视频或图文） */}
      {contentInfo && (
        <ContentCard contentInfo={contentInfo} />
      )}

      {/* 转录卡片 - TranscriptCard */}
      {(transcript || transcriptSegments) && (
        <TranscriptCard
          transcript={transcript}
          segments={transcriptSegments}
        />
      )}

      {/* Markdown/Text 内容 - AI Report */}
      {contentSegments.map((segment, index) => {
        if (segment.type === 'markdown') {
          return (
            <MarkdownBlock
              key={`md-${index}`}
              segment={segment}
              isStreaming={index === contentSegments.length - 1 && isStreaming}
              showReportHeader={index === 0 && showReportHeader}
            />
          );
        }
        if (segment.type === 'text' && segment.content) {
          return (
            <div
              key={`text-${index}`}
              className="text-sm text-text-secondary leading-relaxed whitespace-pre-wrap"
            >
              {segment.content}
            </div>
          );
        }
        return null;
      })}

      {hasMediaResults && (
        <ChatMediaResults
          voices={mediaResults.voices}
          speeches={mediaResults.speeches}
          generations={mediaResults.generations}
        />
      )}

      {/* 如果没有任何内容且正在流式输出，显示加载指示器 */}
      {!hasAnyContent && isStreaming && (
        <div className="flex items-center justify-center gap-3 py-8">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-primary animate-bounce" />
            <div className="w-2 h-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: '0.1s' }} />
            <div className="w-2 h-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: '0.2s' }} />
          </div>
          <span className="text-sm text-text-muted">{t('emptyState.analyzing')}</span>
        </div>
      )}

      {/* 底部操作栏 - 仅在完成后显示 */}
      {!isStreaming && hasAnyContent && (
        <MessageActions
          getMarkdown={getMarkdown}
          onRetry={onRetry}
          showRetry={!!onRetry}
        />
      )}
    </div>
  );
});

const ChatMediaResults = memo(function ChatMediaResults({ voices = [], speeches = [], generations = [] }) {
  const { t } = useTranslation();
  if (voices.length === 0 && speeches.length === 0 && generations.length === 0) return null;

  return (
    <section className="glass-effect p-6 rounded-2xl border border-border-default shadow-xl animate-fade-in">
      {voices.length > 0 && (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-text-primary">{t('mediaAi.voiceCloneTitle')}</h3>
          {voices.map((voice, index) => (
            <div key={`voice-${voice.voiceId || index}`} className="p-4 rounded-xl border border-border-default bg-bg-secondary/40 space-y-3">
              <p className="text-sm text-text-secondary">
                voice_id: <span className="font-mono text-text-primary">{voice.voiceId || '-'}</span>
              </p>
              {voice.fullAudioUrl && (
                <div>
                  <p className="text-xs text-text-muted mb-1">Full Audio</p>
                  <audio className="w-full" controls preload="metadata" src={toPlayableMediaUrl(voice.fullAudioUrl)} />
                </div>
              )}
              {voice.clipAudioUrl && (
                <div>
                  <p className="text-xs text-text-muted mb-1">30s Clip</p>
                  <audio className="w-full" controls preload="metadata" src={toPlayableMediaUrl(voice.clipAudioUrl)} />
                </div>
              )}
              {voice.sampleAudioUrl && (
                <div>
                  <p className="text-xs text-text-muted mb-1">Sample</p>
                  <audio className="w-full" controls preload="metadata" src={toPlayableMediaUrl(voice.sampleAudioUrl)} />
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {speeches.length > 0 && (
        <div className={`${voices.length > 0 ? 'mt-6 pt-6 border-t border-border-default' : ''} space-y-4`}>
          <h3 className="text-lg font-semibold text-text-primary">{t('mediaAi.ttsTitle')}</h3>
          {speeches.map((speech, index) => (
            <SpeechResultCard key={`tts-${speech.audioUrl || index}`} speech={speech} />
          ))}
        </div>
      )}

      {generations.length > 0 && (
        <div className={`${voices.length > 0 || speeches.length > 0 ? 'mt-6 pt-6 border-t border-border-default' : ''} space-y-4`}>
          <h3 className="text-lg font-semibold text-text-primary">{t('mediaAi.lipsyncTitle')}</h3>
          {generations.map((item, index) => (
            <div key={`lip-${item.generationId || item.outputUrl || index}`} className="p-4 rounded-xl border border-border-default bg-bg-secondary/40 space-y-2">
              <div className="flex items-center justify-between gap-2">
                <p className="text-sm text-text-secondary">{item.model || 'lipsync'}</p>
                <span className="text-xs text-text-muted">{item.status || '-'}</span>
              </div>
              {item.outputUrl ? (
                <video className="w-full rounded" controls preload="metadata" src={toPlayableMediaUrl(item.outputUrl)} />
              ) : (
                <p className="text-xs text-text-muted">{t('mediaAi.processingStatus')}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </section>
  );
});

const SpeechResultCard = memo(function SpeechResultCard({ speech }) {
  const { t } = useTranslation();
  const [taggedText, setTaggedText] = useState(speech.taggedText || speech.text || '');
  const [audioUrl, setAudioUrl] = useState(speech.audioUrl || '');
  const [showTags, setShowTags] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const nextTagged = speech.taggedText || speech.text || '';
    setTaggedText(nextTagged);
  }, [speech.taggedText, speech.text]);

  useEffect(() => {
    setAudioUrl(speech.audioUrl || '');
  }, [speech.audioUrl]);

  const insertTag = (tag) => {
    const base = taggedText || speech.text || '';
    if (!base) return;
    const spacer = base && !base.endsWith(' ') ? ' ' : '';
    setTaggedText(`${base}${spacer}${tag} `);
  };

  const handleRegenerate = async () => {
    if (!speech.voiceId) {
      setError('voice_id missing');
      return;
    }
    if (!taggedText.trim()) {
      setError('Tagged text is empty');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const result = await textToSpeech({
        voiceId: speech.voiceId,
        text: taggedText.trim(),
        audioFormat: speech.format || 'mp3',
        speed: typeof speech.speed === 'number' ? speech.speed : null,
        autoEmotion: false,
        autoBreaks: false,
        tagStrategy: 'none',
        speechStyle: 'speech',
        useVoiceProfile: false,
      });
      const nextUrl = normalizeMediaUrl(result?.data?.audio_url || result?.data?.audioUrl || '');
      if (nextUrl) {
        setAudioUrl(nextUrl);
        persistChatMediaResults({
          speeches: [{
            voice_id: speech.voiceId,
            audio_url: nextUrl,
            format: speech.format || 'mp3',
            speed: result?.data?.speed ?? speech.speed,
            text: speech.text || '',
            tagged_text: taggedText.trim(),
            emotion: result?.data?.emotion || '',
            tone_tags: result?.data?.tone_tags || [],
            effect_tags: result?.data?.effect_tags || [],
          }],
        });
      }
    } catch (e) {
      setError(e.message || 'Regenerate failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-4 rounded-xl border border-border-default bg-bg-secondary/40 space-y-3">
      <p className="text-sm text-text-secondary">
        voice_id: <span className="font-mono text-text-primary">{speech.voiceId || '-'}</span>
      </p>
      <p className="text-xs text-text-muted">format: {speech.format || 'mp3'}</p>
      {speech.text && (
        <p className="text-xs text-text-muted whitespace-pre-wrap break-words">{speech.text}</p>
      )}
      <div className="space-y-2">
        <p className="text-xs text-text-secondary">{t('mediaAi.taggedTextPreview')}</p>
        <textarea
          value={taggedText}
          onChange={(e) => setTaggedText(e.target.value)}
          className="w-full bg-bg-tertiary border border-border-default rounded-lg px-3 py-2 text-xs min-h-[120px]"
          placeholder={t('mediaAi.taggedTextPlaceholder')}
        />
        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={() => insertTag('(long-break)')} className="px-2.5 py-1 rounded-md text-[11px] border border-border-default text-text-muted">{t('mediaAi.insertLongBreak')}</button>
          <button type="button" onClick={() => insertTag('(breath)')} className="px-2.5 py-1 rounded-md text-[11px] border border-border-default text-text-muted">{t('mediaAi.insertBreath')}</button>
          <button type="button" onClick={() => insertTag('(laughing)')} className="px-2.5 py-1 rounded-md text-[11px] border border-border-default text-text-muted">{t('mediaAi.insertLaugh')}</button>
          <button type="button" onClick={() => setShowTags((v) => !v)} className="px-2.5 py-1 rounded-md text-[11px] border border-border-default text-text-muted">{t('mediaAi.tagLibrary')}</button>
        </div>
        {showTags && (
          <div className="border border-border-default rounded-lg p-3 space-y-2">
            <p className="text-xs text-text-muted">{t('mediaAi.tagLibraryHint')}</p>
            <div className="space-y-2">
              <p className="text-xs text-text-secondary">{t('mediaAi.ttsEmotionBasic')}</p>
              <div className="flex flex-wrap gap-2">
                {BASIC_EMOTION_TAGS.map((tag) => (
                  <button key={tag} type="button" onClick={() => insertTag(tag)} className="px-2 py-1 rounded-md text-[11px] border border-border-default text-text-muted">{tag}</button>
                ))}
              </div>
            </div>
            <div className="space-y-2">
              <p className="text-xs text-text-secondary">{t('mediaAi.ttsEmotionAdvanced')}</p>
              <div className="flex flex-wrap gap-2">
                {ADVANCED_EMOTION_TAGS.map((tag) => (
                  <button key={tag} type="button" onClick={() => insertTag(tag)} className="px-2 py-1 rounded-md text-[11px] border border-border-default text-text-muted">{tag}</button>
                ))}
              </div>
            </div>
            <div className="space-y-2">
              <p className="text-xs text-text-secondary">{t('mediaAi.ttsToneTags')}</p>
              <div className="flex flex-wrap gap-2">
                {TONE_TAGS.map((tag) => (
                  <button key={tag} type="button" onClick={() => insertTag(tag)} className="px-2 py-1 rounded-md text-[11px] border border-border-default text-text-muted">{tag}</button>
                ))}
              </div>
            </div>
            <div className="space-y-2">
              <p className="text-xs text-text-secondary">{t('mediaAi.ttsEffectTags')}</p>
              <div className="flex flex-wrap gap-2">
                {EFFECT_TAGS.map((tag) => (
                  <button key={tag} type="button" onClick={() => insertTag(tag)} className="px-2 py-1 rounded-md text-[11px] border border-border-default text-text-muted">{tag}</button>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
      {error && <p className="text-xs text-red-400">{error}</p>}
      <button
        type="button"
        onClick={handleRegenerate}
        disabled={loading}
        className="px-3 py-2 rounded-lg text-xs border border-border-default disabled:opacity-50"
      >
        {loading ? t('mediaAi.processing') : t('mediaAi.regenerateSpeech')}
      </button>
      {audioUrl && (
        <audio className="w-full" controls preload="metadata" src={toPlayableMediaUrl(audioUrl)} />
      )}
    </div>
  );
});

export default memo(MessageItem);
