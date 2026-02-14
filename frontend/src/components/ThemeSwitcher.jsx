import React from 'react';
import { useTheme } from '../hooks/useTheme';

/**
 * ThemeSwitcher - Compact theme toggle button
 *
 * Toggles between light and dark themes.
 * Mirrors the LanguageSwitcher style.
 */
function ThemeSwitcher({ className = '' }) {
  const { isDark, toggleTheme } = useTheme();

  return (
    <button
      type="button"
      onClick={toggleTheme}
      className={`
        p-2 rounded-lg transition-colors duration-200
        text-text-secondary hover:text-text-primary hover:bg-bg-tertiary
        focus:outline-none ring-offset-2 focus:ring-2 ring-primary/20
        ${className}
      `}
      title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
      aria-label={isDark ? 'Switch to light theme' : 'Switch to dark theme'}
    >
      <span className="material-symbols-outlined text-xl">
        {isDark ? 'light_mode' : 'dark_mode'}
      </span>
    </button>
  );
}

export default ThemeSwitcher;
