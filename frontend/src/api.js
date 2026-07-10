import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

export const api = axios.create({ baseURL: API_URL });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('merchaudit_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export async function login(email, password) {
  const form = new URLSearchParams();
  form.append('username', email);
  form.append('password', password);
  const { data } = await api.post('/auth/login', form, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });
  return data.access_token;
}

export async function register(email, password, role = 'analyst') {
  const { data } = await api.post('/auth/register', { email, password, role });
  return data;
}

export async function me() {
  const { data } = await api.get('/auth/me');
  return data;
}

export async function createMerchant(payload) {
  const { data } = await api.post('/merchants', payload);
  return data;
}

export async function runAudit(merchantId) {
  const { data } = await api.post(`/merchants/${merchantId}/audit`);
  return data;
}

export async function listReports({ decision, riskBand, page = 1, pageSize = 20 } = {}) {
  const params = { page, page_size: pageSize };
  if (decision) params.decision = decision;
  if (riskBand) params.risk_band = riskBand;
  const { data } = await api.get('/reports', { params });
  return data;
}

export async function getReportsForMerchant(merchantId) {
  const { data } = await api.get(`/reports/${merchantId}`);
  return data;
}
