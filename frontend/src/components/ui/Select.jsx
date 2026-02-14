import React, { useState, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

/**
 * Select - 精美下拉选择组件
 *
 * 设计参考模式选择器，支持:
 * - Material Symbols 图标
 * - 主标题 + 副标题双行显示
 * - 彩色图标
 * - 选中勾选标记
 *
 * @param {Object} props
 * @param {Array} props.options - 选项数组
 *   [{ value, label, subtitle?, icon?, iconColor?, disabled? }]
 *   - icon: Material Symbol 名称 (string) 或 emoji 或 React 元素
 *   - iconColor: 图标颜色类名，如 'text-accent-cyan'
 * @param {string} props.value - 当前选中值
 * @param {Function} props.onChange - 选中回调 (value) => void
 * @param {string} props.placeholder - 占位文本
 * @param {boolean} props.disabled - 是否禁用
 * @param {string} props.className - 额外样式类
 */
function Select({
  options = [],
  value,
  onChange,
  placeholder = 'Select...',
  disabled = false,
  className = '',
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  const [failedLogos, setFailedLogos] = useState(new Set());
  const containerRef = useRef(null);
  const listRef = useRef(null);

  // 当前选中项
  const selectedOption = options.find(opt => opt.value === value);

  // 点击外部关闭
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  // 键盘导航
  const handleKeyDown = useCallback((e) => {
    if (disabled) return;

    switch (e.key) {
      case 'Enter':
      case ' ':
        e.preventDefault();
        if (isOpen) {
          if (highlightedIndex >= 0 && options[highlightedIndex] && !options[highlightedIndex].disabled) {
            onChange(options[highlightedIndex].value);
            setIsOpen(false);
          }
        } else {
          setIsOpen(true);
        }
        break;
      case 'Escape':
        setIsOpen(false);
        break;
      case 'ArrowDown':
        e.preventDefault();
        if (!isOpen) {
          setIsOpen(true);
        } else {
          setHighlightedIndex(prev => {
            const next = prev + 1;
            return next >= options.length ? 0 : next;
          });
        }
        break;
      case 'ArrowUp':
        e.preventDefault();
        if (isOpen) {
          setHighlightedIndex(prev => {
            const next = prev - 1;
            return next < 0 ? options.length - 1 : next;
          });
        }
        break;
      default:
        break;
    }
  }, [disabled, isOpen, highlightedIndex, options, onChange]);

  // 打开时滚动到选中项
  useEffect(() => {
    if (isOpen && listRef.current && value) {
      const selectedIndex = options.findIndex(opt => opt.value === value);
      if (selectedIndex >= 0) {
        setHighlightedIndex(selectedIndex);
        const item = listRef.current.children[selectedIndex];
        if (item) {
          item.scrollIntoView({ block: 'nearest' });
        }
      }
    }
  }, [isOpen, value, options]);

  const handleSelect = (option) => {
    if (option.disabled) return;
    onChange(option.value);
    setIsOpen(false);
  };

  // 渲染图标
  const renderIcon = (option, size = 'text-xl') => {
    // 检查 logo 是否存在且未加载失败
    const hasLogo = option?.logo && !failedLogos.has(option.value);

    // Logo 优先
    if (hasLogo) {
      return (
        <div className="w-6 h-6 flex items-center justify-center flex-shrink-0">
          <img
            src={option.logo}
            alt={option.label || ''}
            className="w-5 h-5 object-contain"
            onError={() => {
              // 记录加载失败，触发重新渲染显示 fallback
              setFailedLogos(prev => new Set(prev).add(option.value));
            }}
          />
        </div>
      );
    }

    // Fallback: 无图标
    if (!option?.icon) return null;

    // Fallback: React 元素
    if (React.isValidElement(option.icon)) {
      return option.icon;
    }

    // Fallback: Material Symbol 图标
    if (typeof option.icon === 'string' && !isEmoji(option.icon)) {
      return (
        <span className={`material-symbols-outlined ${size} ${option.iconColor || 'text-text-muted'}`}>
          {option.icon}
        </span>
      );
    }

    // Fallback: Emoji
    return <span className="text-lg">{option.icon}</span>;
  };

  // 简单判断是否为 emoji
  const isEmoji = (str) => {
    return /[\u{1F300}-\u{1F9FF}]|[\u{2600}-\u{26FF}]/u.test(str);
  };

  return (
    <div
      ref={containerRef}
      className={`relative ${className}`}
      onKeyDown={handleKeyDown}
    >
      {/* Trigger Button */}
      <button
        type="button"
        onClick={() => !disabled && setIsOpen(!isOpen)}
        disabled={disabled}
        className={`
          w-full flex items-center justify-between gap-3
          px-3 py-2.5 bg-sidebar-dark border border-slate-border rounded-lg
          text-sm text-left transition-all duration-200
          ${disabled
            ? 'opacity-50 cursor-not-allowed'
            : 'hover:border-slate-600/80 hover:bg-slate-700/30'
          }
          ${isOpen ? 'border-slate-600 bg-slate-700/30' : ''}
        `}
      >
        <span className="flex items-center gap-3 truncate min-w-0">
          {selectedOption && renderIcon(selectedOption)}
          <span className={`truncate ${selectedOption ? 'text-text-primary' : 'text-text-muted'}`}>
            {selectedOption?.label || placeholder}
          </span>
        </span>
        <span className={`
          material-symbols-outlined text-sm text-text-muted transition-transform duration-200 flex-shrink-0
          ${isOpen ? 'rotate-180' : ''}
        `}>
          expand_more
        </span>
      </button>

      {/* Dropdown */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.15, ease: 'easeOut' }}
            className="
              absolute z-50 w-full mt-2
              bg-card-dark border border-slate-border rounded-xl
              shadow-xl shadow-black/30
              overflow-hidden
            "
          >
            <ul
              ref={listRef}
              className="max-h-72 overflow-y-auto custom-scrollbar py-1"
              role="listbox"
            >
              {options.map((option, index) => {
                const isSelected = option.value === value;
                const isHighlighted = index === highlightedIndex;
                const isDisabled = option.disabled;

                return (
                  <li
                    key={option.value}
                    role="option"
                    aria-selected={isSelected}
                    onClick={() => handleSelect(option)}
                    onMouseEnter={() => !isDisabled && setHighlightedIndex(index)}
                    className={`
                      flex items-center gap-3 px-4 py-3 cursor-pointer
                      transition-all duration-150
                      ${isDisabled
                        ? 'opacity-40 cursor-not-allowed'
                        : isSelected
                          ? 'bg-slate-700/50'
                          : isHighlighted
                            ? 'bg-slate-700/30'
                            : 'hover:bg-slate-700/30'
                      }
                    `}
                  >
                    {/* Icon */}
                    {renderIcon(option)}

                    {/* Label & Subtitle */}
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium text-text-primary truncate">
                        {option.label}
                      </div>
                      {option.subtitle && (
                        <div className="text-xs text-text-muted truncate">
                          {option.subtitle}
                        </div>
                      )}
                    </div>

                    {/* Checkmark */}
                    {isSelected && (
                      <span className="material-symbols-outlined text-sm text-accent-cyan flex-shrink-0">
                        check
                      </span>
                    )}
                  </li>
                );
              })}
            </ul>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default Select;
