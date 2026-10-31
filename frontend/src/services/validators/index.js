/**
 * Client-side usability validators (mirrored and enforced authoritatively on the FastAPI backend).
 */

export const validateEmail = (email) => {
  if (!email || !email.trim()) return 'Email address is required.';
  const re = /^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/;
  if (!re.test(email.trim())) return 'Please enter a valid email address.';
  return null;
};

export const validatePasswordPolicy = (password) => {
  if (!password || password.length < 8) {
    return 'Password must be at least 8 characters long.';
  }
  if (!/[A-Z]/.test(password)) {
    return 'Password must include at least one uppercase letter.';
  }
  if (!/[a-z]/.test(password)) {
    return 'Password must include at least one lowercase letter.';
  }
  if (!/[!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?`~]/.test(password)) {
    return 'Password must include at least one special character (e.g. !@#$%^&*).';
  }
  return null;
};

export const formatCurrency = (val) => {
  const num = Number(val ?? 0);
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(Number.isFinite(num) ? num : 0);
};

