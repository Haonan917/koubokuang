/**
 * Card Component - Modern Minimal Design
 *
 * A unified card component for consistent styling across the app.
 *
 * Variants:
 * - default: Standard card with border
 * - elevated: Card with shadow that lifts on hover
 * - glass: Semi-transparent card with backdrop blur
 */
import React from 'react';

const variants = {
  default: `
    bg-bg-secondary
    border border-border-default
    hover:border-border-subtle
  `,
  elevated: `
    bg-bg-secondary
    border border-border-default
    shadow-lg shadow-black/5
    hover:shadow-xl hover:shadow-black/10
    hover:border-border-subtle
  `,
  glass: `
    bg-bg-secondary/80
    backdrop-blur-xl
    border border-border-default
    hover:border-border-subtle
  `,
  flat: `
    bg-bg-tertiary/50
    border border-transparent
    hover:bg-bg-tertiary
  `,
};

const paddings = {
  none: '',
  sm: 'p-4',
  md: 'p-6',
  lg: 'p-8',
};

export default function Card({
  children,
  variant = 'default',
  padding = 'md',
  rounded = 'xl',
  className = '',
  onClick,
  as: Component = 'div',
  ...props
}) {
  const baseStyles = `
    transition-all duration-200
    ${rounded === 'xl' ? 'rounded-xl' : rounded === 'lg' ? 'rounded-lg' : 'rounded-2xl'}
    ${onClick ? 'cursor-pointer' : ''}
  `;

  return (
    <Component
      onClick={onClick}
      className={`${baseStyles} ${variants[variant]} ${paddings[padding]} ${className}`}
      {...props}
    >
      {children}
    </Component>
  );
}

/**
 * CardHeader Component
 *
 * A header section for cards with title and optional actions.
 */
export function CardHeader({ children, className = '', actions }) {
  return (
    <div className={`flex items-center justify-between mb-4 ${className}`}>
      <div className="flex items-center gap-3">{children}</div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}

/**
 * CardTitle Component
 *
 * A title for cards with consistent styling.
 */
export function CardTitle({ children, icon, className = '' }) {
  return (
    <h3 className={`font-display font-semibold text-lg text-text-primary flex items-center gap-2 ${className}`}>
      {icon && (
        <span className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
          <span className="material-symbols-outlined text-primary text-lg">{icon}</span>
        </span>
      )}
      {children}
    </h3>
  );
}

/**
 * CardDescription Component
 *
 * A description text for cards.
 */
export function CardDescription({ children, className = '' }) {
  return <p className={`text-text-secondary text-sm leading-relaxed ${className}`}>{children}</p>;
}

/**
 * CardContent Component
 *
 * A content wrapper for cards.
 */
export function CardContent({ children, className = '' }) {
  return <div className={className}>{children}</div>;
}

/**
 * CardFooter Component
 *
 * A footer section for cards, typically for actions.
 */
export function CardFooter({ children, className = '' }) {
  return (
    <div className={`flex items-center justify-end gap-3 mt-6 pt-4 border-t border-border-default ${className}`}>
      {children}
    </div>
  );
}
