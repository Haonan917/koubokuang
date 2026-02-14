import React from 'react';
import { useTranslation } from 'react-i18next';
import { ADVANCED_EMOTION_TAGS, BASIC_EMOTION_TAGS, EFFECT_TAGS, TONE_TAGS } from '../../utils/ttsTags';

function TTSTagControls({
  emotionTag = '',
  toneTags = [],
  effectTags = [],
  onEmotionChange,
  onToneTagsChange,
  onEffectTagsChange,
  showEmotion = true,
  showTone = true,
  showEffect = true,
}) {
  const { t } = useTranslation();

  const toggleTag = (currentTags, tag, onChange) => {
    if (!onChange) return;
    const exists = currentTags.includes(tag);
    onChange(exists ? currentTags.filter((item) => item !== tag) : [...currentTags, tag]);
  };

  return (
    <div className="space-y-3 border border-border-default rounded-lg p-3">
      {showEmotion && (
        <div>
          <label className="text-sm font-medium text-text-secondary">{t('mediaAi.ttsEmotion')}</label>
          <select
            value={emotionTag}
            onChange={(e) => onEmotionChange?.(e.target.value)}
            className="mt-2 w-full bg-bg-tertiary border border-border-default rounded-lg px-3 py-2 text-sm"
          >
            <option value="">{t('mediaAi.ttsEmotionNone')}</option>
            <optgroup label={t('mediaAi.ttsEmotionBasic')}>
              {BASIC_EMOTION_TAGS.map((tag) => (
                <option key={tag} value={tag}>{tag}</option>
              ))}
            </optgroup>
            <optgroup label={t('mediaAi.ttsEmotionAdvanced')}>
              {ADVANCED_EMOTION_TAGS.map((tag) => (
                <option key={tag} value={tag}>{tag}</option>
              ))}
            </optgroup>
          </select>
          <p className="text-xs text-text-muted mt-1">{t('mediaAi.ttsTagRuleEmotion')}</p>
        </div>
      )}

      {showTone && (
        <div>
          <label className="text-sm font-medium text-text-secondary">{t('mediaAi.ttsToneTags')}</label>
          <div className="mt-2 flex flex-wrap gap-2">
            {TONE_TAGS.map((tag) => {
              const active = toneTags.includes(tag);
              return (
                <button
                  key={tag}
                  type="button"
                  onClick={() => toggleTag(toneTags, tag, onToneTagsChange)}
                  className={`px-2.5 py-1 rounded-md text-xs border ${
                    active ? 'bg-primary/10 border-primary/50 text-primary' : 'border-border-default text-text-muted'
                  }`}
                >
                  {tag}
                </button>
              );
            })}
          </div>
          <p className="text-xs text-text-muted mt-1">{t('mediaAi.ttsTagRuleTone')}</p>
        </div>
      )}

      {showEffect && (
        <div>
          <label className="text-sm font-medium text-text-secondary">{t('mediaAi.ttsEffectTags')}</label>
          <div className="mt-2 flex flex-wrap gap-2">
            {EFFECT_TAGS.map((tag) => {
              const active = effectTags.includes(tag);
              return (
                <button
                  key={tag}
                  type="button"
                  onClick={() => toggleTag(effectTags, tag, onEffectTagsChange)}
                  className={`px-2.5 py-1 rounded-md text-xs border ${
                    active ? 'bg-primary/10 border-primary/50 text-primary' : 'border-border-default text-text-muted'
                  }`}
                >
                  {tag}
                </button>
              );
            })}
          </div>
          <p className="text-xs text-text-muted mt-1">{t('mediaAi.ttsTagRuleEffect')}</p>
        </div>
      )}
    </div>
  );
}

export default TTSTagControls;
