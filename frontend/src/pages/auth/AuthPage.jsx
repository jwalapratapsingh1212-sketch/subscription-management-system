import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { KeyRound, Lock, Mail, ShieldCheck, UserPlus } from 'lucide-react';
import { authApi, extractErrorMessage } from '../../services/api/client';
import { useAuth } from '../../services/auth/AuthContext';
import { validateEmail, validatePasswordPolicy } from '../../services/validators';
import { ToastBanner } from '../../components/common/UI';

export const AuthPage = () => {
  const [mode, setMode] = useState('login'); // login | register | forgot | reset
  const [email, setEmail] = useState('admin@submanage.io');
  const [password, setPassword] = useState('Admin@12345');
  const [fullName, setFullName] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [phone, setPhone] = useState('');
  const [billingAddress, setBillingAddress] = useState('');
  const [resetToken, setResetToken] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [toast, setToast] = useState(null);

  const { login, register } = useAuth();
  const navigate = useNavigate();

  const fillDemoAccount = (demoEmail, demoPass) => {
    setMode('login');
    setEmail(demoEmail);
    setPassword(demoPass);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setToast(null);

    if (mode === 'login') {
      const emailErr = validateEmail(email);
      if (emailErr) return setToast({ type: 'error', message: emailErr });
      setSubmitting(true);
      try {
        const u = await login(email, password);
        navigate(u.role === 'customer' ? '/portal' : '/dashboard');
      } catch (err) {
        setToast({ type: 'error', message: extractErrorMessage(err) });
      } finally {
        setSubmitting(false);
      }
    } else if (mode === 'register') {
      const emailErr = validateEmail(email);
      if (emailErr) return setToast({ type: 'error', message: emailErr });
      const passErr = validatePasswordPolicy(password);
      if (passErr) return setToast({ type: 'error', message: passErr });

      setSubmitting(true);
      try {
        await register({
          email,
          password,
          full_name: fullName,
          company_name: companyName || null,
          phone: phone || null,
          billing_address: billingAddress || '',
        });
        navigate('/portal');
      } catch (err) {
        setToast({ type: 'error', message: extractErrorMessage(err) });
      } finally {
        setSubmitting(false);
      }
    } else if (mode === 'forgot') {
      setSubmitting(true);
      try {
        const res = await authApi.forgotPassword(email);
        if (res.reset_token) {
          setResetToken(res.reset_token);
          setMode('reset');
          setToast({
            type: 'success',
            message: 'Reset token generated and pre-filled below. Enter your new password.',
          });
        } else {
          setToast({ type: 'success', message: res.message });
        }
      } catch (err) {
        setToast({ type: 'error', message: extractErrorMessage(err) });
      } finally {
        setSubmitting(false);
      }
    } else if (mode === 'reset') {
      const passErr = validatePasswordPolicy(newPassword);
      if (passErr) return setToast({ type: 'error', message: passErr });
      setSubmitting(true);
      try {
        const res = await authApi.resetPassword({
          reset_token: resetToken,
          new_password: newPassword,
        });
        setToast({ type: 'success', message: res.message });
        setMode('login');
        setPassword(newPassword);
      } catch (err) {
        setToast({ type: 'error', message: extractErrorMessage(err) });
      } finally {
        setSubmitting(false);
      }
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col justify-center items-center p-4">
      <ToastBanner toast={toast} onClose={() => setToast(null)} />
      <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl p-8">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg">
            <ShieldCheck className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">SubManage Enterprise</h1>
            <p className="text-xs text-slate-400">
              Subscription Lifecycle, Automated Billing & Finance OS
            </p>
          </div>
        </div>

        {/* Mode Tabs */}
        <div className="grid grid-cols-3 gap-1 bg-slate-950 p-1 rounded-xl mb-6 border border-slate-800 text-xs font-semibold">
          <button
            type="button"
            onClick={() => setMode('login')}
            className={`py-2 rounded-lg transition ${
              mode === 'login' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
            }`}
          >
            Sign In
          </button>
          <button
            type="button"
            onClick={() => setMode('register')}
            className={`py-2 rounded-lg transition ${
              mode === 'register' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
            }`}
          >
            Customer Sign Up
          </button>
          <button
            type="button"
            onClick={() => setMode('forgot')}
            className={`py-2 rounded-lg transition ${
              mode === 'forgot' || mode === 'reset'
                ? 'bg-indigo-600 text-white'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Reset Password
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {mode !== 'reset' && (
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Email Address</label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl pl-9 pr-3 py-2.5 text-sm text-white focus:border-indigo-500 focus:outline-none"
                  placeholder="you@company.com"
                  required
                />
              </div>
            </div>
          )}

          {mode === 'register' && (
            <>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Full Name</label>
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white"
                  placeholder="Jane Doe"
                  required
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Company</label>
                  <input
                    type="text"
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white"
                    placeholder="Acme Inc."
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Phone</label>
                  <input
                    type="text"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white"
                    placeholder="+1 555-0100"
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Billing Address
                </label>
                <input
                  type="text"
                  value={billingAddress}
                  onChange={(e) => setBillingAddress(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white"
                  placeholder="100 Enterprise Way, Suite 200"
                />
              </div>
            </>
          )}

          {(mode === 'login' || mode === 'register') && (
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Password{' '}
                {mode === 'register' && (
                  <span className="text-[11px] text-slate-400">
                    (8+ chars, upper, lower & special)
                  </span>
                )}
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl pl-9 pr-3 py-2.5 text-sm text-white focus:border-indigo-500 focus:outline-none"
                  required
                />
              </div>
            </div>
          )}

          {mode === 'reset' && (
            <>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Password Reset Token
                </label>
                <input
                  type="text"
                  value={resetToken}
                  onChange={(e) => setResetToken(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white font-mono"
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  New Password (8+ chars, upper, lower & special)
                </label>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white"
                  required
                />
              </div>
            </>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="w-full py-2.5 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm shadow-lg shadow-indigo-600/25 disabled:opacity-50 transition"
          >
            {submitting
              ? 'Processing...'
              : mode === 'login'
              ? 'Sign In to Workspace'
              : mode === 'register'
              ? 'Create Customer Account'
              : mode === 'forgot'
              ? 'Generate Password Reset Token'
              : 'Complete Password Reset'}
          </button>
        </form>

        {/* Demo Quick Switcher */}
        <div className="mt-6 pt-5 border-t border-slate-800">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 mb-2.5">
            Quick Demo Role Login (One-Click Populate)
          </div>
          <div className="grid grid-cols-3 gap-2">
            <button
              type="button"
              onClick={() => fillDemoAccount('admin@submanage.io', 'Admin@12345')}
              className="px-2.5 py-2 rounded-lg bg-purple-500/10 border border-purple-500/30 text-purple-300 text-xs font-medium hover:bg-purple-500/20"
            >
              System Admin
            </button>
            <button
              type="button"
              onClick={() => fillDemoAccount('staff@submanage.io', 'Staff@12345')}
              className="px-2.5 py-2 rounded-lg bg-blue-500/10 border border-blue-500/30 text-blue-300 text-xs font-medium hover:bg-blue-500/20"
            >
              Internal Staff
            </button>
            <button
              type="button"
              onClick={() => fillDemoAccount('alice@acmecloud.io', 'Customer@123')}
              className="px-2.5 py-2 rounded-lg bg-teal-500/10 border border-teal-500/30 text-teal-300 text-xs font-medium hover:bg-teal-500/20"
            >
              Customer Portal
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

