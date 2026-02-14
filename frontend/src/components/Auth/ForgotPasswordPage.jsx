/**
 * Forgot Password Page - Modern Minimal Design
 */
import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { forgotPassword } from '../../services/auth';

export default function ForgotPasswordPage() {
  const { t } = useTranslation();

  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!email) {
      setError(t('auth.emailRequired'));
      return;
    }

    setLoading(true);

    try {
      await forgotPassword(email);
      setSuccess(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bg-primary px-4">
        <div className="w-full max-w-md text-center">
          {/* Success icon */}
          <div className="w-16 h-16 mx-auto mb-6 bg-success/10 border border-success/20 rounded-full flex items-center justify-center">
            <span className="material-symbols-outlined text-4xl text-success">mail</span>
          </div>

          <h2 className="text-xl font-semibold text-text-primary mb-2">
            {t('auth.resetEmailSent')}
          </h2>

          <p className="text-text-secondary mb-6">
            {t('auth.resetEmailSentDesc')}
          </p>

          <Link
            to="/auth/login"
            className="inline-block px-6 py-2.5 bg-primary hover:bg-primary-hover text-white font-medium rounded-lg transition-colors"
          >
            {t('auth.backToLogin')}
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg-primary px-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <Link to="/" className="inline-flex items-center gap-3">
            <img src="/assets/logo_width.png" alt="Logo" className="h-10 object-contain" />
            <div className="text-left">
              <h1 className="font-display font-bold text-lg text-text-primary">
                {t('app.name')}
              </h1>
              <p className="text-[10px] text-text-muted font-medium uppercase tracking-widest">
                {t('app.tagline')}
              </p>
            </div>
          </Link>
        </div>

        {/* Form */}
        <div className="bg-bg-secondary border border-border-default rounded-xl p-8">
          <h2 className="text-xl font-semibold text-text-primary mb-2 text-center">
            {t('auth.forgotPasswordTitle')}
          </h2>

          <p className="text-text-secondary text-sm mb-6 text-center">
            {t('auth.forgotPasswordDesc')}
          </p>

          {error && (
            <div className="mb-4 p-3 bg-error/10 border border-error/20 rounded-lg text-error text-sm flex items-start gap-2">
              <span className="material-symbols-outlined text-lg flex-shrink-0">error</span>
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-1.5">
                {t('auth.email')}
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder={t('auth.emailPlaceholder')}
                className="w-full px-4 py-2.5 bg-bg-primary border border-border-default rounded-lg text-text-primary placeholder-text-muted focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all"
                disabled={loading}
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 bg-primary hover:bg-primary-hover text-white font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? t('auth.sending') : t('auth.sendResetLink')}
            </button>
          </form>
        </div>

        {/* Back to login */}
        <p className="mt-6 text-center text-text-secondary text-sm">
          <Link to="/auth/login" className="text-primary hover:text-primary-hover font-medium transition-colors">
            {t('auth.backToLogin')}
          </Link>
        </p>
      </div>
    </div>
  );
}
