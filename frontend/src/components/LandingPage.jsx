/**
 * Landing Page - OpenClaw Dark Theme
 *
 * A premium dark landing page with scarlet accents and glow effects.
 * Features gradient backgrounds, floating orbs, and enhanced hover states.
 */
import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import LanguageSwitcher from '../i18n/LanguageSwitcher';
import ThemeSwitcher from './ThemeSwitcher';

// Platform configurations
const PLATFORMS = [
  { key: 'xhs', logo: '/assets/logos/xhs.png' },
  { key: 'douyin', logo: '/assets/logos/dy.png' },
  { key: 'bilibili', logo: '/assets/logos/bili.png' },
  { key: 'kuaishou', logo: '/assets/logos/ks.png' },
];

// Feature configurations
const FEATURES = [
  { key: 'multiPlatform', icon: 'language' },
  { key: 'aiAnalysis', icon: 'psychology' },
  { key: 'creativeRemix', icon: 'auto_awesome' },
];

// Platform badge component with glow hover
function PlatformBadge({ platform }) {
  const { t } = useTranslation();

  return (
    <div className="group flex items-center gap-3 px-4 py-2.5 rounded-xl bg-bg-secondary border border-border-default hover:border-primary/30 hover:bg-bg-tertiary transition-all duration-200 cursor-default">
      <img
        src={platform.logo}
        alt={t(`platforms.${platform.key}`)}
        className="w-5 h-5 object-contain opacity-70 group-hover:opacity-100 transition-opacity"
      />
      <span className="text-sm font-medium text-text-secondary group-hover:text-text-primary transition-colors">
        {t(`platforms.${platform.key}`)}
      </span>
    </div>
  );
}

// Feature card with glow effect
function FeatureCard({ feature, index }) {
  const { t } = useTranslation();

  return (
    <div
      className="feature-card-glow animate-fade-in"
      style={{ animationDelay: `${index * 100}ms` }}
    >
      {/* Icon with glow */}
      <div className="feature-icon-glow">
        <span className="material-symbols-outlined text-primary text-2xl">{feature.icon}</span>
      </div>

      <h3 className="font-display text-lg font-semibold text-text-primary mb-3">
        {t(`landing.features.${feature.key}.title`)}
      </h3>

      <p className="text-text-secondary text-sm leading-relaxed">
        {t(`landing.features.${feature.key}.description`)}
      </p>
    </div>
  );
}

// Step indicator with gradient number
function StepIndicator({ step, isLast }) {
  const { t } = useTranslation();

  return (
    <div className="flex flex-col items-center text-center relative">
      {/* Step number with gradient */}
      <div className="step-number-gradient mb-5">
        {step}
      </div>

      {/* Connecting line for desktop */}
      {!isLast && (
        <div className="hidden md:block absolute top-6 left-[calc(50%+32px)] w-[calc(100%-64px)] h-px bg-gradient-to-r from-primary/30 to-transparent" />
      )}

      <h3 className="font-display text-base font-semibold text-text-primary mb-2">
        {t(`landing.steps.step${step}.title`)}
      </h3>

      <p className="text-text-secondary text-sm max-w-[200px] leading-relaxed">
        {t(`landing.steps.step${step}.description`)}
      </p>
    </div>
  );
}

function LandingPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const handleLogin = () => navigate('/auth/login');
  const handleRegister = () => navigate('/auth/register');

  return (
    <div className="min-h-screen bg-bg-primary text-text-primary overflow-hidden">
      {/* ===== Header ===== */}
      <header className="fixed top-0 left-0 right-0 z-50 glass-effect">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          {/* Logo */}
          <div
            className="flex items-center gap-3 cursor-pointer group"
            onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
          >
            <img src="/assets/logo_width.png" alt="Logo" className="h-10 object-contain" />
            <div className="flex flex-col">
              <span className="font-display text-base font-bold text-text-primary">
                {t('app.name')}
              </span>
              <span className="text-[10px] text-text-muted font-bold tracking-widest uppercase">
                {t('app.tagline')}
              </span>
            </div>
          </div>

          {/* Navigation */}
          <nav className="flex items-center gap-3">
            <ThemeSwitcher />
            <LanguageSwitcher />
            <button
              onClick={handleLogin}
              className="px-4 py-2 text-sm font-medium text-text-secondary hover:text-text-primary hover:bg-bg-tertiary rounded-lg transition-all"
            >
              {t('auth.login')}
            </button>
            <button
              onClick={handleRegister}
              className="btn-primary"
            >
              {t('auth.register')}
            </button>
          </nav>
        </div>
      </header>

      {/* ===== Hero Section ===== */}
      <section className="relative pt-36 pb-24 px-6">
        {/* Background glow orbs */}
        <div className="hero-glow-orb hero-glow-orb-1" />
        <div className="hero-glow-orb hero-glow-orb-2" />

        <div className="max-w-4xl mx-auto text-center relative z-10">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 border border-primary/20 mb-10 animate-fade-in">
            <span className="w-2 h-2 rounded-full bg-primary animate-pulse" />
            <span className="text-sm font-semibold text-primary">{t('landing.badge')}</span>
          </div>

          {/* Main heading - Large and bold */}
          <h1 className="text-5xl sm:text-6xl md:text-7xl font-display font-bold leading-[1.1] mb-8 animate-fade-in stagger-1">
            <span className="text-text-primary block">
              {t('landing.heroTitle').split('，')[0]}
            </span>
            {t('landing.heroTitle').split('，')[1] && (
              <span className="text-primary block mt-2">
                {t('landing.heroTitle').split('，')[1]}
              </span>
            )}
          </h1>

          {/* Subtitle */}
          <p className="text-lg md:text-xl text-text-secondary max-w-2xl mx-auto mb-12 leading-relaxed animate-fade-in stagger-2">
            {t('landing.heroSubtitle')}
          </p>

          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-20 animate-fade-in stagger-3">
            <button
              onClick={handleRegister}
              className="btn-cta-glow"
            >
              <span className="material-symbols-outlined text-xl">rocket_launch</span>
              {t('landing.getStarted')}
            </button>
            <button
              onClick={handleLogin}
              className="px-8 py-4 text-base font-semibold text-text-primary bg-bg-secondary hover:bg-bg-tertiary border border-border-default hover:border-border-subtle rounded-xl transition-all"
            >
              {t('landing.haveAccount')}
            </button>
          </div>

          {/* Platforms */}
          <div className="animate-fade-in stagger-4">
            <p className="text-xs font-bold text-text-muted uppercase tracking-[0.2em] mb-5">
              {t('landing.supportedPlatforms')}
            </p>
            <div className="flex flex-wrap items-center justify-center gap-3">
              {PLATFORMS.map((platform, index) => (
                <div key={platform.key} style={{ animationDelay: `${400 + index * 80}ms` }} className="animate-fade-in">
                  <PlatformBadge platform={platform} />
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ===== Features Section ===== */}
      <section className="py-24 px-6 border-t border-border-default relative">
        <div className="max-w-5xl mx-auto">
          {/* Section header */}
          <div className="text-center mb-16">
            <span className="inline-block px-4 py-1.5 rounded-lg bg-primary/10 text-primary text-xs font-bold uppercase tracking-wider mb-5">
              Features
            </span>
            <h2 className="font-display text-3xl md:text-5xl font-bold text-text-primary mb-5">
              {t('landing.featuresTitle')}
            </h2>
            <p className="text-text-secondary text-lg max-w-xl mx-auto">
              {t('landing.featuresSubtitle')}
            </p>
          </div>

          {/* Features grid */}
          <div className="grid md:grid-cols-3 gap-6">
            {FEATURES.map((feature, index) => (
              <FeatureCard key={feature.key} feature={feature} index={index} />
            ))}
          </div>
        </div>
      </section>

      {/* ===== How It Works Section ===== */}
      <section className="py-24 px-6 border-t border-border-default">
        <div className="max-w-4xl mx-auto">
          {/* Section header */}
          <div className="text-center mb-20">
            <span className="inline-block px-4 py-1.5 rounded-lg bg-primary/10 text-primary text-xs font-bold uppercase tracking-wider mb-5">
              How It Works
            </span>
            <h2 className="font-display text-3xl md:text-5xl font-bold text-text-primary mb-5">
              {t('landing.howItWorksTitle')}
            </h2>
            <p className="text-text-secondary text-lg">
              {t('landing.howItWorksSubtitle')}
            </p>
          </div>

          {/* Steps */}
          <div className="grid md:grid-cols-3 gap-16 md:gap-8 relative">
            {[1, 2, 3].map((step, index) => (
              <StepIndicator key={step} step={step} index={index} isLast={index === 2} />
            ))}
          </div>
        </div>
      </section>

      {/* ===== Final CTA Section ===== */}
      <section className="py-24 px-6 border-t border-border-default relative overflow-hidden">
        {/* Background glow */}
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="w-[600px] h-[600px] rounded-full bg-primary/5 blur-[100px]" />
        </div>

        <div className="max-w-2xl mx-auto text-center relative z-10">
          {/* Pulsing Logo */}
          <div className="flex items-center justify-center mx-auto mb-8 logo-pulse">
            <img src="/assets/logo_width.png" alt="Logo" className="h-20 object-contain" />
          </div>

          <h2 className="font-display text-3xl md:text-5xl font-bold text-text-primary mb-5">
            {t('landing.ctaTitle')}
          </h2>

          <p className="text-text-secondary text-lg mb-10 max-w-md mx-auto">
            {t('landing.ctaSubtitle')}
          </p>

          <button
            onClick={handleRegister}
            className="btn-cta-glow"
          >
            <span className="material-symbols-outlined text-xl">arrow_forward</span>
            {t('landing.ctaButton')}
          </button>
        </div>
      </section>

      {/* ===== Footer ===== */}
      <footer className="py-10 px-6 border-t border-border-default">
        <div className="max-w-5xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-bg-tertiary flex items-center justify-center">
              <span className="material-symbols-outlined text-text-muted text-lg">bolt</span>
            </div>
            <span className="text-text-secondary text-sm">
              {t('app.name')}
              <span className="mx-2 text-border-subtle">·</span>
              {t('app.tagline')}
            </span>
          </div>

          <div className="text-text-muted text-xs">
            {t('landing.copyright', { year: new Date().getFullYear() })}
          </div>
        </div>
      </footer>
    </div>
  );
}

export default LandingPage;
