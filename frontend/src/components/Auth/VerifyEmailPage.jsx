/**
 * Verify Email Page - Modern Minimal Design
 */
import React, { useEffect, useState } from 'react';
import { Link, useSearchParams, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { verifyEmail, resendVerification } from '../../services/auth';
import { useAuth } from '../../hooks/useAuth';

export default function VerifyEmailPage() {
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { user, isEmailVerified, updateUser } = useAuth();

  const token = searchParams.get('token');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [verifySuccess, setVerifySuccess] = useState(false);
  const [resendSuccess, setResendSuccess] = useState(false);
  const [resendCooldown, setResendCooldown] = useState(0);

  // Auto verify if token present
  useEffect(() => {
    if (token) {
      handleVerify();
    }
  }, [token]);

  // Resend cooldown countdown
  useEffect(() => {
    if (resendCooldown > 0) {
      const timer = setTimeout(() => setResendCooldown(resendCooldown - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [resendCooldown]);

  const handleVerify = async () => {
    setLoading(true);
    setError('');

    try {
      await verifyEmail(token);
      setVerifySuccess(true);
      // Update user state
      if (updateUser) {
        updateUser({ email_verified: true });
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    if (resendCooldown > 0) return;

    setLoading(true);
    setError('');
    setResendSuccess(false);

    try {
      await resendVerification();
      setResendSuccess(true);
      setResendCooldown(60); // 60 second cooldown
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Verify success
  if (verifySuccess) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bg-primary px-4">
        <div className="w-full max-w-md text-center">
          <div className="w-16 h-16 mx-auto mb-6 bg-success/10 border border-success/20 rounded-full flex items-center justify-center">
            <span className="material-symbols-outlined text-4xl text-success">verified</span>
          </div>

          <h2 className="text-xl font-semibold text-text-primary mb-2">
            {t('auth.emailVerified')}
          </h2>

          <p className="text-text-secondary mb-6">
            {t('auth.emailVerifiedDesc')}
          </p>

          <Link
            to="/"
            className="inline-block px-6 py-2.5 bg-primary hover:bg-primary-hover text-white font-medium rounded-lg transition-colors"
          >
            {t('auth.startUsing')}
          </Link>
        </div>
      </div>
    );
  }

  // Verifying with token
  if (token && loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bg-primary px-4">
        <div className="w-full max-w-md text-center">
          <div className="w-16 h-16 mx-auto mb-6 relative">
            <div className="absolute inset-0 border-4 border-border-default rounded-full" />
            <div className="absolute inset-0 border-4 border-primary border-t-transparent rounded-full animate-spin" />
          </div>

          <h2 className="text-xl font-semibold text-text-primary mb-2">
            {t('auth.verifyingEmail')}
          </h2>

          <p className="text-text-secondary">
            {t('auth.pleaseWait')}
          </p>
        </div>
      </div>
    );
  }

  // Token verification failed
  if (token && error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bg-primary px-4">
        <div className="w-full max-w-md text-center">
          <div className="w-16 h-16 mx-auto mb-6 bg-error/10 border border-error/20 rounded-full flex items-center justify-center">
            <span className="material-symbols-outlined text-4xl text-error">error</span>
          </div>

          <h2 className="text-xl font-semibold text-text-primary mb-2">
            {t('auth.verifyFailed')}
          </h2>

          <p className="text-text-secondary mb-6">{error}</p>

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

  // Waiting for verification (user logged in but not verified)
  return (
    <div className="min-h-screen flex items-center justify-center bg-bg-primary px-4">
      <div className="w-full max-w-md text-center">
        <div className="w-16 h-16 mx-auto mb-6 bg-warning/10 border border-warning/20 rounded-full flex items-center justify-center">
          <span className="material-symbols-outlined text-4xl text-warning">mail</span>
        </div>

        <h2 className="text-xl font-semibold text-text-primary mb-2">
          {t('auth.verifyYourEmail')}
        </h2>

        <p className="text-text-secondary mb-6">
          {t('auth.verifyEmailDesc', { email: user?.email || '' })}
        </p>

        {error && (
          <div className="mb-4 p-3 bg-error/10 border border-error/20 rounded-lg text-error text-sm">
            {error}
          </div>
        )}

        {resendSuccess && (
          <div className="mb-4 p-3 bg-success/10 border border-success/20 rounded-lg text-success text-sm">
            {t('auth.verifyEmailResent')}
          </div>
        )}

        <div className="space-y-3">
          <button
            onClick={handleResend}
            disabled={loading || resendCooldown > 0}
            className="w-full py-2.5 bg-primary hover:bg-primary-hover text-white font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {resendCooldown > 0
              ? t('auth.resendIn', { seconds: resendCooldown })
              : loading
                ? t('auth.sending')
                : t('auth.resendEmail')}
          </button>

          <Link
            to="/"
            className="block w-full py-2.5 border border-border-default text-text-secondary hover:text-text-primary hover:border-border-subtle font-medium rounded-lg transition-all"
          >
            {t('auth.skipForNow')}
          </Link>
        </div>
      </div>
    </div>
  );
}
