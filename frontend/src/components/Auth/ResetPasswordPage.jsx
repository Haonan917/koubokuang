/**
 * Reset Password Page - Modern Minimal Design
 */
import React, { useState } from 'react';
import { Link, useSearchParams, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { resetPassword } from '../../services/auth';

export default function ResetPasswordPage() {
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const token = searchParams.get('token');

  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  // Invalid link
  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bg-primary px-4">
        <div className="w-full max-w-md text-center">
          <div className="w-16 h-16 mx-auto mb-6 bg-error/10 border border-error/20 rounded-full flex items-center justify-center">
            <span className="material-symbols-outlined text-4xl text-error">error</span>
          </div>

          <h2 className="text-xl font-semibold text-text-primary mb-2">
            {t('auth.invalidResetLink')}
          </h2>

          <p className="text-text-secondary mb-6">
            {t('auth.invalidResetLinkDesc')}
          </p>

          <Link
            to="/auth/forgot-password"
            className="inline-block px-6 py-2.5 bg-primary hover:bg-primary-hover text-white font-medium rounded-lg transition-colors"
          >
            {t('auth.requestNewLink')}
          </Link>
        </div>
      </div>
    );
  }

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    // Validation
    if (!password) {
      setError(t('auth.passwordRequired'));
      return;
    }

    if (password.length < 6) {
      setError(t('auth.passwordTooShort'));
      return;
    }

    if (password !== confirmPassword) {
      setError(t('auth.passwordMismatch'));
      return;
    }

    setLoading(true);

    try {
      await resetPassword(token, password);
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
          <div className="w-16 h-16 mx-auto mb-6 bg-success/10 border border-success/20 rounded-full flex items-center justify-center">
            <span className="material-symbols-outlined text-4xl text-success">check_circle</span>
          </div>

          <h2 className="text-xl font-semibold text-text-primary mb-2">
            {t('auth.passwordResetSuccess')}
          </h2>

          <p className="text-text-secondary mb-6">
            {t('auth.passwordResetSuccessDesc')}
          </p>

          <Link
            to="/auth/login"
            className="inline-block px-6 py-2.5 bg-primary hover:bg-primary-hover text-white font-medium rounded-lg transition-colors"
          >
            {t('auth.loginNow')}
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
          <h2 className="text-xl font-semibold text-text-primary mb-6 text-center">
            {t('auth.resetPasswordTitle')}
          </h2>

          {error && (
            <div className="mb-4 p-3 bg-error/10 border border-error/20 rounded-lg text-error text-sm flex items-start gap-2">
              <span className="material-symbols-outlined text-lg flex-shrink-0">error</span>
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-1.5">
                {t('auth.newPassword')}
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder={t('auth.newPasswordPlaceholder')}
                className="w-full px-4 py-2.5 bg-bg-primary border border-border-default rounded-lg text-text-primary placeholder-text-muted focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all"
                disabled={loading}
              />
              <p className="mt-1 text-xs text-text-muted">{t('auth.passwordHint')}</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-text-secondary mb-1.5">
                {t('auth.confirmNewPassword')}
              </label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder={t('auth.confirmNewPasswordPlaceholder')}
                className="w-full px-4 py-2.5 bg-bg-primary border border-border-default rounded-lg text-text-primary placeholder-text-muted focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all"
                disabled={loading}
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 bg-primary hover:bg-primary-hover text-white font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? t('auth.resetting') : t('auth.resetPassword')}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
