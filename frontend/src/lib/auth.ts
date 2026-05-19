import { create } from "zustand";

type AuthState = {
  token: string | null;
  setToken: (token: string | null) => void;
};

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem("swaflow_token"),
  setToken: (token) => {
    if (token) {
      localStorage.setItem("swaflow_token", token);
    } else {
      localStorage.removeItem("swaflow_token");
    }
    set({ token });
  },
}));

