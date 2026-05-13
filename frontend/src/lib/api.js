import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({
  baseURL: API,
  timeout: 15000,
});

api.interceptors.request.use((cfg) => {
  try {
    const t = localStorage.getItem("scalper_token");
    if (t) cfg.headers.Authorization = `Bearer ${t}`;
  } catch {}
  return cfg;
});

export function wsUrl(path) {
  if (!BACKEND_URL) return path;
  const u = BACKEND_URL.replace(/^http/, "ws");
  return `${u}${path}`;
}
