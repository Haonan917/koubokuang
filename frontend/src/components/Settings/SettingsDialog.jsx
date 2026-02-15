import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Settings as SettingsIcon, Palette, Mic, AudioLines, Clapperboard, Camera } from 'lucide-react';
import InsightModeManager from './InsightModeManager';
import VoiceCloneManager from './VoiceCloneManager';
import AvatarCloneManager from './AvatarCloneManager';
import TTSManager from './TTSManager';
import LipsyncManager from './LipsyncManager';

/**
 * 设置菜单配置
 * 可扩展添加更多设置项
 */
const getMenuItems = (t) => [
  {
    key: 'modes',
    icon: Palette,
    label: t('insightModes.title'),
  },
  {
    key: 'voice_clone',
    icon: Mic,
    label: t('mediaAi.voiceCloneTitle'),
  },
  {
    key: 'avatar_clone',
    icon: Camera,
    label: t('mediaAi.avatarCloneTitle'),
  },
  {
    key: 'tts',
    icon: AudioLines,
    label: t('mediaAi.ttsTitle'),
  },
  {
    key: 'lipsync',
    icon: Clapperboard,
    label: t('mediaAi.lipsyncTitle'),
  },
  // 未来可添加更多设置项
  // { key: 'general', icon: SettingsIcon, label: t('settings.general') },
];

/**
 * SettingsDialog - 设置弹窗
 *
 * 左侧菜单 + 右侧内容区域的设置界面
 * 可扩展添加更多设置项
 */
function SettingsDialog({ isOpen, onClose }) {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState('modes');

  const menuItems = getMenuItems(t);

  // ESC 关闭
  React.useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
    };
  }, [isOpen, onClose]);

  // 点击遮罩关闭
  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  // 渲染右侧内容
  const renderContent = () => {
    switch (activeTab) {
      case 'modes':
        return <InsightModeManager />;
      case 'voice_clone':
        return <VoiceCloneManager />;
      case 'avatar_clone':
        return <AvatarCloneManager />;
      case 'tts':
        return <TTSManager />;
      case 'lipsync':
        return <LipsyncManager />;
      default:
        return null;
    }
  };

  const modalContent = (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
          onClick={handleBackdropClick}
        >
          <motion.div
            className="w-full max-w-6xl h-[85vh] max-h-[900px] bg-bg-secondary border border-border-default rounded-2xl shadow-2xl overflow-hidden flex flex-col mx-4"
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ duration: 0.2, ease: 'easeOut' }}
          >
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-border-default">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-primary/10 rounded-lg flex items-center justify-center">
                  <SettingsIcon size={18} className="text-primary" />
                </div>
                <h2 className="text-lg font-semibold text-text-primary">{t('settings.title')}</h2>
              </div>
              <button
                onClick={onClose}
                className="p-2 text-text-muted hover:text-text-primary hover:bg-white/5 rounded-lg transition-colors"
                aria-label="Close"
              >
                <X size={20} />
              </button>
            </div>

            {/* Body: Left Menu + Right Content */}
            <div className="flex-1 flex overflow-hidden">
              {/* Left Menu */}
              <nav className="w-56 border-r border-border-default p-4 flex-shrink-0">
                <div className="space-y-1">
                  {menuItems.map((item) => {
                    const Icon = item.icon;
                    const isActive = activeTab === item.key;
                    return (
                      <button
                        key={item.key}
                        onClick={() => setActiveTab(item.key)}
                        className={`
                          w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left text-sm font-medium transition-all
                          ${isActive
                            ? 'bg-primary/10 text-primary border border-primary/20'
                            : 'text-text-secondary hover:text-text-primary hover:bg-white/5 border border-transparent'
                          }
                        `}
                      >
                        <Icon size={18} />
                        {item.label}
                      </button>
                    );
                  })}
                </div>
              </nav>

              {/* Right Content */}
              <div className="flex-1 p-6 overflow-y-auto custom-scrollbar">
                {renderContent()}
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );

  return createPortal(modalContent, document.body);
}

export default SettingsDialog;
