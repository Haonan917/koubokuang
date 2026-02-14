/**
 * Button Component - OpenClaw Dark Theme
 *
 * A unified button component with multiple variants featuring
 * gradient backgrounds and glow effects.
 *
 * Variants:
 * - primary: Red gradient with glow effect for primary actions
 * - secondary: Dark background with subtle border for secondary actions
 * - ghost: Transparent button for tertiary actions
 * - danger: Red button for destructive actions
 * - glow: Enhanced primary with stronger glow (for CTAs)
 *
 * Sizes:
 * - sm: Small padding and text
 * - md: Default size
 * - lg: Large padding and text
 */
import React from 'react';

const variants = {
  primary: `
    bg-gradient-to-br from-primary to-primary-active
    text-white
    shadow-[0_4px_20px_rgba(255,59,59,0.3)]
    hover:shadow-[0_6px_30px_rgba(255,59,59,0.4)]
    hover:-translate-y-0.5
    active:translate-y-0
    active:shadow-[0_2px_10px_rgba(255,59,59,0.3)]
  `,
  secondary: `
    bg-bg-secondary hover:bg-bg-tertiary
    text-text-primary
    border border-border-default hover:border-border-subtle
  `,
  ghost: `
    bg-transparent hover:bg-bg-tertiary
    text-text-secondary hover:text-text-primary
  `,
  danger: `
    bg-error hover:bg-error/90
    text-white
  `,
  glow: `
    bg-gradient-to-br from-primary to-primary-active
    text-white
    shadow-[0_4px_30px_rgba(255,59,59,0.4)]
    hover:shadow-[0_6px_40px_rgba(255,59,59,0.5)]
    hover:-translate-y-0.5
    active:translate-y-0
    active:shadow-[0_2px_15px_rgba(255,59,59,0.4)]
  `,
};

const sizes = {
  sm: 'px-3 py-1.5 text-xs gap-1.5',
  md: 'px-4 py-2 text-sm gap-2',
  lg: 'px-6 py-3 text-base gap-2',
};

export default function Button({
  children,
  variant = 'primary',
  size = 'md',
  disabled = false,
  loading = false,
  icon,
  iconRight,
  className = '',
  ...props
}) {
  const baseStyles = `
    inline-flex items-center justify-center
    font-display font-semibold
    rounded-lg
    transition-all duration-150
    focus:outline-none focus:ring-2 focus:ring-primary/50 focus:ring-offset-2 focus:ring-offset-bg-primary
    disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none disabled:shadow-none
  `;

  return (
    <button
      disabled={disabled || loading}
      className={`${baseStyles} ${variants[variant]} ${sizes[size]} ${className}`}
      {...props}
    >
      {loading ? (
        <>
          <span className="material-symbols-outlined animate-spin text-[1em]">progress_activity</span>
          <span>{children}</span>
        </>
      ) : (
        <>
          {icon && <span className="material-symbols-outlined text-[1.2em]">{icon}</span>}
          <span>{children}</span>
          {iconRight && <span className="material-symbols-outlined text-[1.2em]">{iconRight}</span>}
        </>
      )}
    </button>
  );
}

/**
 * IconButton Component
 *
 * A square button that only contains an icon.
 */
export function IconButton({
  icon,
  variant = 'ghost',
  size = 'md',
  disabled = false,
  className = '',
  ...props
}) {
  const baseStyles = `
    inline-flex items-center justify-center
    rounded-lg
    transition-all duration-150
    focus:outline-none focus:ring-2 focus:ring-primary/50
    disabled:opacity-50 disabled:cursor-not-allowed
  `;

  const iconSizes = {
    sm: 'w-7 h-7 text-sm',
    md: 'w-9 h-9 text-base',
    lg: 'w-11 h-11 text-lg',
  };

  return (
    <button
      disabled={disabled}
      className={`${baseStyles} ${variants[variant]} ${iconSizes[size]} ${className}`}
      {...props}
    >
      <span className="material-symbols-outlined">{icon}</span>
    </button>
  );
}

/**
 * CTAButton Component
 *
 * A large call-to-action button with enhanced glow effect.
 * Use for hero sections and important conversion points.
 */
export function CTAButton({
  children,
  icon,
  iconRight,
  disabled = false,
  loading = false,
  className = '',
  ...props
}) {
  return (
    <button
      disabled={disabled || loading}
      className={`
        inline-flex items-center justify-center gap-3
        px-8 py-4 text-base
        font-display font-semibold
        rounded-xl
        bg-gradient-to-br from-primary to-primary-active
        text-white
        shadow-[0_4px_30px_rgba(255,59,59,0.4)]
        hover:shadow-[0_6px_40px_rgba(255,59,59,0.5)]
        hover:-translate-y-0.5
        active:translate-y-0
        transition-all duration-200
        focus:outline-none focus:ring-2 focus:ring-primary/50 focus:ring-offset-2 focus:ring-offset-bg-primary
        disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none disabled:shadow-none
        ${className}
      `}
      {...props}
    >
      {loading ? (
        <>
          <span className="material-symbols-outlined animate-spin text-xl">progress_activity</span>
          <span>{children}</span>
        </>
      ) : (
        <>
          {icon && <span className="material-symbols-outlined text-xl">{icon}</span>}
          <span>{children}</span>
          {iconRight && <span className="material-symbols-outlined text-xl">{iconRight}</span>}
        </>
      )}
    </button>
  );
}
