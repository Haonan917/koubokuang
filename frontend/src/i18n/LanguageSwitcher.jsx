import React from 'react';
import { useTranslation } from 'react-i18next';
import { getCurrentLanguage, toggleLanguage } from './index';

/**
 * LanguageSwitcher - Compact language toggle button
 *
 * Toggles between English and Chinese with a single click.
 * Shows current language indicator (EN / 中).
 */
function LanguageSwitcher({ className = '' }) {
  const { i18n } = useTranslation();
  const currentLang = getCurrentLanguage();
  const isEnglish = currentLang === 'en';

  const handleToggle = () => {
    toggleLanguage();
  };

  return (
    <button
      type="button"
      onClick={handleToggle}
      className={`
        p-2 rounded-lg transition-colors duration-200
        text-text-secondary hover:text-text-primary hover:bg-bg-tertiary
        font-medium text-sm
        ${className}
      `}
      title={isEnglish ? '点击切换中文' : 'Switch to English'}
      aria-label={isEnglish ? 'Switch to Chinese' : '切换到英文'}
    >
      {/* 
        这里可以只显示图标，或者显示当前语言的简称。
        为了极简，我们显示"对方"语言的简称，引导用户点击切换？
        或者显示一个通用的翻译图标。
        
        方案：显示 standard translate icon + 当前语言标识 (EN/中) 
        或者更极简： EN / 中 text only.
      */}
      <div className="flex items-center gap-1">
        <span className="material-symbols-outlined text-xl">translate</span>
        {/* <span className="text-xs font-bold uppercase">{isEnglish ? 'EN' : '中'}</span> */}
      </div>
    </button>
  );
}

export default LanguageSwitcher;
