/**
 * Login Page - OpenClaw Dark Theme
 */
import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../hooks/useAuth';
import { getOAuthAuthorizeUrl } from '../../services/auth';

export default function LoginPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const { login, loading, error, clearError, oauthProviders } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [localError, setLocalError] = useState('');

  const from = location.state?.from || '/';

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLocalError('');
    clearError();

    if (!email || !password) {
      setLocalError(t('auth.fieldsRequired'));
      return;
    }

    try {
      await login(email, password);
      navigate(from, { replace: true });
    } catch (err) {
      // Error handled in useAuth
    }
  };

  const handleOAuth = async (provider) => {
    try {
      const data = await getOAuthAuthorizeUrl(provider);
      window.location.href = data.authorize_url;
    } catch (err) {
      setLocalError(err.message);
    }
  };

  const displayError = localError || error;

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg-primary px-4 relative overflow-hidden">
      {/* Background glow */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[500px] h-[500px] rounded-full bg-primary/5 blur-[100px] pointer-events-none" />

      <div className="w-full max-w-md relative z-10">
        {/* Logo */}
        <div className="text-center mb-10">
          <Link to="/" className="inline-flex items-center gap-3 group">
            <img src="/assets/logo_width.png" alt="Logo" className="h-12 object-contain" />
            <div className="text-left">
              <h1 className="font-display font-bold text-xl text-text-primary">
                {t('app.name')}
              </h1>
              <p className="text-[10px] text-text-muted font-bold uppercase tracking-widest">
                {t('app.tagline')}
              </p>
            </div>
          </Link>
        </div>

        {/* Login form */}
        <div className="card-glow p-8">
          <h2 className="text-xl font-display font-bold text-text-primary mb-8 text-center">
            {t('auth.loginTitle')}
          </h2>

          {displayError && (
            <div className="mb-6 p-4 bg-error/10 border border-error/20 rounded-lg text-error text-sm flex items-start gap-3">
              <span className="material-symbols-outlined text-lg flex-shrink-0">error</span>
              <span>{displayError}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-sm font-semibold text-text-secondary mb-2">
                {t('auth.email')}
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder={t('auth.emailPlaceholder')}
                className="w-full px-4 py-3 bg-bg-tertiary border border-border-default rounded-lg text-text-primary placeholder-text-muted focus:outline-none focus:border-primary/50 focus:ring-2 focus:ring-primary/10 focus:shadow-[0_0_20px_rgba(255,59,59,0.05)] transition-all"
                disabled={loading}
              />
            </div>

            <div>
              <label className="block text-sm font-semibold text-text-secondary mb-2">
                {t('auth.password')}
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder={t('auth.passwordPlaceholder')}
                className="w-full px-4 py-3 bg-bg-tertiary border border-border-default rounded-lg text-text-primary placeholder-text-muted focus:outline-none focus:border-primary/50 focus:ring-2 focus:ring-primary/10 focus:shadow-[0_0_20px_rgba(255,59,59,0.05)] transition-all"
                disabled={loading}
              />
            </div>

            <div className="flex justify-end">
              <Link
                to="/auth/forgot-password"
                className="text-sm font-medium text-primary hover:text-primary-hover transition-colors"
              >
                {t('auth.forgotPassword')}
              </Link>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-gradient-to-br from-primary to-primary-active text-white font-semibold rounded-lg transition-all shadow-[0_4px_20px_rgba(255,59,59,0.3)] hover:shadow-[0_6px_30px_rgba(255,59,59,0.4)] hover:-translate-y-0.5 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none disabled:shadow-none"
            >
              {loading ? t('auth.loggingIn') : t('auth.login')}
            </button>
          </form>

          {/* OAuth divider */}
          {(oauthProviders.github || oauthProviders.google) && (
            <>
              <div className="relative my-8">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-border-default" />
                </div>
                <div className="relative flex justify-center text-sm">
                  <span className="px-4 bg-bg-secondary text-text-muted">
                    {t('auth.orContinueWith')}
                  </span>
                </div>
              </div>

              {/* OAuth buttons */}
              <div className="space-y-3">
                {oauthProviders.github && (
                  <button
                    onClick={() => handleOAuth('github')}
                    disabled={loading}
                    className="w-full flex items-center justify-center gap-3 py-3 bg-bg-tertiary hover:bg-bg-elevated text-text-primary font-semibold rounded-lg border border-border-default hover:border-border-subtle transition-all disabled:opacity-50"
                  >
                    <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
                    </svg>
                    {t('auth.continueWithGithub')}
                  </button>
                )}

                {oauthProviders.google && (
                  <button
                    onClick={() => handleOAuth('google')}
                    disabled={loading}
                    className="w-full flex items-center justify-center gap-3 py-3 bg-bg-tertiary hover:bg-bg-elevated text-text-primary font-semibold rounded-lg border border-border-default hover:border-border-subtle transition-all disabled:opacity-50"
                  >
                    <svg className="w-5 h-5" viewBox="0 0 24 24">
                      <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                      <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                      <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
                    </svg>
                    {t('auth.continueWithGoogle')}
                  </button>
                )}
              </div>
            </>
          )}
        </div>

        {/* Register link */}
        <p className="mt-8 text-center text-text-secondary text-sm">
          {t('auth.noAccount')}{' '}
          <Link to="/auth/register" className="text-primary hover:text-primary-hover font-semibold transition-colors">
            {t('auth.registerNow')}
          </Link>
        </p>
      </div>
    </div>
  );
}
