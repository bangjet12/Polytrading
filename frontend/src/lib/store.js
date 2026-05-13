import { create } from "zustand";

export const useAuthStore = create((set) => ({
  token: typeof window !== "undefined" ? localStorage.getItem("scalper_token") || null : null,
  email: typeof window !== "undefined" ? localStorage.getItem("scalper_email") || null : null,
  setAuth: (token, email) => {
    try {
      if (token) localStorage.setItem("scalper_token", token);
      else localStorage.removeItem("scalper_token");
      if (email) localStorage.setItem("scalper_email", email);
      else localStorage.removeItem("scalper_email");
    } catch {}
    set({ token, email });
  },
  logout: () => {
    try {
      localStorage.removeItem("scalper_token");
      localStorage.removeItem("scalper_email");
    } catch {}
    set({ token: null, email: null });
  },
}));

export const useStateStore = create((set) => ({
  snapshot: null,
  setSnapshot: (s) => set({ snapshot: s }),
}));
