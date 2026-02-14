import React, { useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';

/**
 * Modal - 通用模态框组件
 *
 * Remix AI Studio 风格的 Modal，支持:
 * - framer-motion 动画
 * - ESC 关闭
 * - 点击遮罩关闭
 * - createPortal 渲染到 body
 */
function Modal({
  isOpen,
  onClose,
  title,
  children,
  headerActions,
  maxWidth = '4xl',
}) {
  // ESC 关闭
  const handleKeyDown = useCallback(
    (e) => {
      if (e.key === 'Escape') {
        onClose();
      }
    },
    [onClose]
  );

  useEffect(() => {
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'hidden';
    }
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
    };
  }, [isOpen, handleKeyDown]);

  // 点击遮罩关闭
  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  const maxWidthClasses = {
    sm: 'max-w-sm',
    md: 'max-w-md',
    lg: 'max-w-lg',
    xl: 'max-w-xl',
    '2xl': 'max-w-2xl',
    '3xl': 'max-w-3xl',
    '4xl': 'max-w-4xl',
    '5xl': 'max-w-5xl',
  };

  const modalContent = (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          className="modal-backdrop"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
          onClick={handleBackdropClick}
        >
          <motion.div
            className={`modal-container ${maxWidthClasses[maxWidth] || 'max-w-4xl'}`}
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ duration: 0.2, ease: 'easeOut' }}
          >
            {/* Header */}
            <div className="modal-header">
              <div className="modal-header-left">
                <button
                  onClick={onClose}
                  className="modal-close-btn"
                  aria-label="Close"
                >
                  <X size={18} />
                </button>
                {title && <h2 className="modal-title">{title}</h2>}
              </div>
              {headerActions && (
                <div className="modal-header-actions">{headerActions}</div>
              )}
            </div>

            {/* Content */}
            <div className="modal-content">{children}</div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );

  return createPortal(modalContent, document.body);
}

export default Modal;
