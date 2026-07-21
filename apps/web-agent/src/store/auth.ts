import { create } from "zustand";

type AuthState = {
  token: string | null;
  setToken: (token: string | null) => void;
  logout: () => void;
};

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem("sm_access_token"),
  setToken: (token) => {
    if (token) localStorage.setItem("sm_access_token", token);
    else localStorage.removeItem("sm_access_token");
    set({ token });
  },
  logout: () => {
    localStorage.removeItem("sm_access_token");
    localStorage.removeItem("sm_refresh_token");
    set({ token: null });
  },
}));
