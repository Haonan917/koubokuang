import React, { memo } from 'react';
import Zap from 'lucide-react/dist/esm/icons/zap';

/**
 * Header - 顶部导航栏
 *
 * ViralAI 风格的深色主题导航栏
 * 包含 Logo、平台标识、标题和操作按钮
 */
function Header({ platform }) {
  return (
    <header className="flex items-center justify-between px-6 py-4 border-b border-border-default bg-bg-primary">
      {/* 左侧: Logo + 平台标签 */}
      <div className="flex items-center gap-4">
        {/* Logo */}
        <div className="flex items-center gap-2">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-accent-cyan to-accent-purple flex items-center justify-center">
            <Zap className="w-5 h-5 text-white" />
          </div>
          <span className="text-lg font-bold text-text-primary tracking-tight">
            Remix<span className="text-accent-cyan">Agent</span>
          </span>
        </div>

        {/* 平台标签 */}
        {platform && (
          <div className="badge badge-cyan">
            <PlatformIcon platform={platform} />
            <span className="ml-1.5">{getPlatformName(platform)}</span>
          </div>
        )}
      </div>

      {/* 中间: 页面标题 */}
      <div className="hidden md:flex items-center gap-2">
        <span className="text-sm text-text-muted">Post Case Study</span>
      </div>

    </header>
  );
}

/**
 * 平台图标组件
 */
function PlatformIcon({ platform }) {
  const iconMap = {
    xhs: '📕',
    dy: '🎵',
    douyin: '🎵',
    bili: '📺',
    bilibili: '📺',
    ks: '⚡',
    kuaishou: '⚡',
  };

  return <span className="text-sm">{iconMap[platform] || '🔗'}</span>;
}

/**
 * 获取平台名称
 */
function getPlatformName(platform) {
  const nameMap = {
    xhs: '小红书',
    dy: '抖音',
    douyin: '抖音',
    bili: 'B站',
    bilibili: 'B站',
    ks: '快手',
    kuaishou: '快手',
  };

  return nameMap[platform] || platform;
}

export default memo(Header);
