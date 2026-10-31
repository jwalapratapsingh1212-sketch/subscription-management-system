import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('sms_access_token');
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const extractErrorMessage = (error) => {
  if (error?.response?.data?.detail) {
    const detail = error.response.data.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
      return detail.map((d) => `${d.loc?.slice(-1)?.[0] || 'field'}: ${d.msg}`).join('; ');
    }
  }
  return error?.message || 'An unexpected error occurred.';
};

export const authApi = {
  login: (data) => apiClient.post('/auth/login', data).then((r) => r.data),
  register: (data) => apiClient.post('/auth/register', data).then((r) => r.data),
  logout: () => apiClient.post('/auth/logout').then((r) => r.data),
  me: () => apiClient.get('/auth/me').then((r) => r.data),
  forgotPassword: (email) => apiClient.post('/auth/forgot-password', { email }).then((r) => r.data),
  resetPassword: (data) => apiClient.post('/auth/reset-password', data).then((r) => r.data),
  createStaff: (data) => apiClient.post('/auth/staff', data).then((r) => r.data),
  listUsers: () => apiClient.get('/auth/users').then((r) => r.data),
  updateUser: (id, data) => apiClient.patch(`/auth/users/${id}`, data).then((r) => r.data),
};

export const customersApi = {
  list: (params) => apiClient.get('/customers', { params }).then((r) => r.data),
  get: (id) => apiClient.get(`/customers/${id}`).then((r) => r.data),
  getMyProfile: () => apiClient.get('/customers/me/profile').then((r) => r.data),
  create: (data) => apiClient.post('/customers', data).then((r) => r.data),
  update: (id, data) => apiClient.patch(`/customers/${id}`, data).then((r) => r.data),
};

export const productsApi = {
  list: (params) => apiClient.get('/products', { params }).then((r) => r.data),
  get: (id) => apiClient.get(`/products/${id}`).then((r) => r.data),
  create: (data) => apiClient.post('/products', data).then((r) => r.data),
  update: (id, data) => apiClient.patch(`/products/${id}`, data).then((r) => r.data),
  createVariant: (productId, data) =>
    apiClient.post(`/products/${productId}/variants`, data).then((r) => r.data),
  updateVariant: (productId, variantId, data) =>
    apiClient.patch(`/products/${productId}/variants/${variantId}`, data).then((r) => r.data),
};

export const plansApi = {
  list: (params) => apiClient.get('/plans', { params }).then((r) => r.data),
  get: (id) => apiClient.get(`/plans/${id}`).then((r) => r.data),
  create: (data) => apiClient.post('/plans', data).then((r) => r.data),
  update: (id, data) => apiClient.patch(`/plans/${id}`, data).then((r) => r.data),
};

export const quotationsApi = {
  list: (params) => apiClient.get('/quotations', { params }).then((r) => r.data),
  get: (id) => apiClient.get(`/quotations/${id}`).then((r) => r.data),
  create: (data) => apiClient.post('/quotations', data).then((r) => r.data),
  update: (id, data) => apiClient.patch(`/quotations/${id}`, data).then((r) => r.data),
  confirm: (id, data = { activate_immediately: true }) =>
    apiClient.post(`/quotations/${id}/confirm`, data).then((r) => r.data),
  listTemplates: () => apiClient.get('/quotations/templates').then((r) => r.data),
  createTemplate: (data) => apiClient.post('/quotations/templates', data).then((r) => r.data),
};

export const subscriptionsApi = {
  list: (params) => apiClient.get('/subscriptions', { params }).then((r) => r.data),
  get: (id) => apiClient.get(`/subscriptions/${id}`).then((r) => r.data),
  create: (data) => apiClient.post('/subscriptions', data).then((r) => r.data),
  update: (id, data) => apiClient.patch(`/subscriptions/${id}`, data).then((r) => r.data),
  sendQuote: (id) => apiClient.post(`/subscriptions/${id}/send-quote`).then((r) => r.data),
  confirm: (id) => apiClient.post(`/subscriptions/${id}/confirm`).then((r) => r.data),
  activate: (id) => apiClient.post(`/subscriptions/${id}/activate`).then((r) => r.data),
  pause: (id) => apiClient.post(`/subscriptions/${id}/pause`).then((r) => r.data),
  resume: (id) => apiClient.post(`/subscriptions/${id}/resume`).then((r) => r.data),
  renew: (id) => apiClient.post(`/subscriptions/${id}/renew`).then((r) => r.data),
  close: (id) => apiClient.post(`/subscriptions/${id}/close`).then((r) => r.data),
};

export const invoicesApi = {
  list: (params) => apiClient.get('/invoices', { params }).then((r) => r.data),
  get: (id) => apiClient.get(`/invoices/${id}`).then((r) => r.data),
  generate: (data) => apiClient.post('/invoices/generate', data).then((r) => r.data),
  confirm: (id) => apiClient.post(`/invoices/${id}/confirm`).then((r) => r.data),
  cancel: (id) => apiClient.post(`/invoices/${id}/cancel`).then((r) => r.data),
  getBalance: (id) => apiClient.get(`/invoices/${id}/balance`).then((r) => r.data),
  getPrintHtml: (id) => apiClient.get(`/invoices/${id}/print`).then((r) => r.data),
};

export const discountsApi = {
  list: (params) => apiClient.get('/discounts', { params }).then((r) => r.data),
  create: (data) => apiClient.post('/discounts', data).then((r) => r.data),
  update: (id, data) => apiClient.patch(`/discounts/${id}`, data).then((r) => r.data),
};

export const taxRulesApi = {
  list: (params) => apiClient.get('/tax-rules', { params }).then((r) => r.data),
  create: (data) => apiClient.post('/tax-rules', data).then((r) => r.data),
  update: (id, data) => apiClient.patch(`/tax-rules/${id}`, data).then((r) => r.data),
};

export const paymentsApi = {
  list: (params) => apiClient.get('/payments', { params }).then((r) => r.data),
  record: (data, idempotencyKey) =>
    apiClient
      .post('/payments', data, {
        headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {},
      })
      .then((r) => r.data),
};

export const reportsApi = {
  dashboard: (params) => apiClient.get('/reports/dashboard', { params }).then((r) => r.data),
  overdue: (params) => apiClient.get('/reports/overdue', { params }).then((r) => r.data),
  revenue: (params) => apiClient.get('/reports/revenue', { params }).then((r) => r.data),
  auditLogs: (params) => apiClient.get('/reports/audit-logs', { params }).then((r) => r.data),
  portal: () => apiClient.get('/reports/portal').then((r) => r.data),
};

export default apiClient;

