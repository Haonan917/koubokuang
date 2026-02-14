import React, { useState, useRef, useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { useTranslation } from 'react-i18next';

/**
 * Popconfirm - 气泡确认框组件
 *
 * 使用 Portal 渲染到 body 层级，避免被父容器 overflow 裁剪
 * 支持确认/取消操作，点击外部自动关闭
 */
function Popconfirm({
  children,
  title,
  confirmText,
  cancelText,
  onConfirm,
  onCancel,
  placement = 'right',
}) {
  const { t } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);
  const [position, setPosition] = useState({ top: 0, left: 0 });
  const triggerRef = useRef(null);
  const popoverRef = useRef(null);

  // Provide default values using translation
  const displayTitle = title ?? t('common.deleteConfirm');
  const displayConfirmText = confirmText ?? t('common.confirm');
  const displayCancelText = cancelText ?? t('common.cancel');

  // 计算气泡位置
  const updatePosition = useCallback(() => {
    if (!triggerRef.current) return;

    const rect = triggerRef.current.getBoundingClientRect();
    const popoverWidth = 160; // 预估宽度
    const popoverHeight = 80; // 预估高度
    const gap = 8;

    let top, left;

    switch (placement) {
      case 'right':
        top = rect.top + rect.height / 2 - popoverHeight / 2;
        left = rect.right + gap;
        break;
      case 'left':
        top = rect.top + rect.height / 2 - popoverHeight / 2;
        left = rect.left - popoverWidth - gap;
        break;
      case 'top':
        top = rect.top - popoverHeight - gap;
        left = rect.left + rect.width / 2 - popoverWidth / 2;
        break;
      case 'bottom':
      default:
        top = rect.bottom + gap;
        left = rect.left + rect.width / 2 - popoverWidth / 2;
        break;
    }

    // 边界检测，确保不超出视窗
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;

    // 右边界检测
    if (left + popoverWidth > viewportWidth - 10) {
      left = viewportWidth - popoverWidth - 10;
    }
    // 左边界检测
    if (left < 10) {
      left = 10;
    }
    // 下边界检测
    if (top + popoverHeight > viewportHeight - 10) {
      top = viewportHeight - popoverHeight - 10;
    }
    // 上边界检测
    if (top < 10) {
      top = 10;
    }

    setPosition({ top, left });
  }, [placement]);

  // 打开时计算位置
  useEffect(() => {
    if (isOpen) {
      updatePosition();
      // 监听滚动和调整大小
      window.addEventListener('scroll', updatePosition, true);
      window.addEventListener('resize', updatePosition);
      return () => {
        window.removeEventListener('scroll', updatePosition, true);
        window.removeEventListener('resize', updatePosition);
      };
    }
  }, [isOpen, updatePosition]);

  // 点击外部关闭
  useEffect(() => {
    if (!isOpen) return;

    function handleClickOutside(event) {
      if (
        popoverRef.current &&
        !popoverRef.current.contains(event.target) &&
        triggerRef.current &&
        !triggerRef.current.contains(event.target)
      ) {
        setIsOpen(false);
        onCancel?.();
      }
    }

    // 延迟添加监听器，避免当前点击事件触发关闭
    const timer = setTimeout(() => {
      document.addEventListener('mousedown', handleClickOutside);
    }, 0);

    return () => {
      clearTimeout(timer);
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen, onCancel]);

  // ESC 键关闭
  useEffect(() => {
    if (!isOpen) return;

    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        setIsOpen(false);
        onCancel?.();
      }
    }

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onCancel]);

  const handleTriggerClick = (e) => {
    e.stopPropagation();
    setIsOpen(true);
  };

  const handleConfirm = (e) => {
    e.stopPropagation();
    setIsOpen(false);
    onConfirm?.();
  };

  const handleCancel = (e) => {
    e.stopPropagation();
    setIsOpen(false);
    onCancel?.();
  };

  // 动画方向
  const animationVariants = {
    right: { initial: { opacity: 0, x: -8 }, animate: { opacity: 1, x: 0 } },
    left: { initial: { opacity: 0, x: 8 }, animate: { opacity: 1, x: 0 } },
    top: { initial: { opacity: 0, y: 8 }, animate: { opacity: 1, y: 0 } },
    bottom: { initial: { opacity: 0, y: -8 }, animate: { opacity: 1, y: 0 } },
  };

  return (
    <>
      {/* Trigger */}
      <div ref={triggerRef} onClick={handleTriggerClick} className="inline-block">
        {children}
      </div>

      {/* Popover - 使用 Portal 渲染到 body */}
      {createPortal(
        <AnimatePresence>
          {isOpen && (
            <motion.div
              ref={popoverRef}
              initial={animationVariants[placement].initial}
              animate={animationVariants[placement].animate}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ duration: 0.15, ease: 'easeOut' }}
              style={{
                position: 'fixed',
                top: position.top,
                left: position.left,
                zIndex: 9999,
              }}
              className="bg-slate-800 border border-slate-700 rounded-lg shadow-xl min-w-[140px] p-3"
            >
              {/* Content */}
              <p className="text-sm text-text-secondary mb-3 whitespace-nowrap">
                {displayTitle}
              </p>

              {/* Buttons */}
              <div className="flex gap-2 justify-end">
                <button
                  type="button"
                  onClick={handleCancel}
                  className="px-3 py-1.5 text-xs font-medium text-text-muted hover:text-text-secondary hover:bg-slate-700/50 rounded-md transition-colors"
                >
                  {displayCancelText}
                </button>
                <button
                  type="button"
                  onClick={handleConfirm}
                  className="px-3 py-1.5 text-xs font-medium text-white bg-accent-pink hover:bg-accent-pink/80 rounded-md transition-colors"
                >
                  {displayConfirmText}
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>,
        document.body
      )}
    </>
  );
}

export default Popconfirm;
