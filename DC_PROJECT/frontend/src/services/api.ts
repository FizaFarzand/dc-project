import axios, { AxiosError } from "axios";

const baseURL =
  import.meta.env.VITE_API_URL?.replace(/\/$/, "") ??
  "http://localhost:8000/api";

export const api = axios.create({
  baseURL,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err: AxiosError) => {
    if (err.response?.status === 401) {
      localStorage.removeItem("access_token");
      const path = window.location.pathname;
      if (!path.startsWith("/login") && !path.startsWith("/register")) {
        window.location.assign("/login");
      }
    }
    return Promise.reject(err);
  },
);

export function getErrorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const status = err.response?.status;
    const data = err.response?.data as { detail?: unknown } | undefined;
    if (data?.detail !== undefined) {
      const d = data.detail;
      if (typeof d === "string") return d;
      if (Array.isArray(d))
        return d.map((x) => (typeof x === "object" ? JSON.stringify(x) : String(x))).join("; ");
    }
    if (status === 500) return "Server error";
    if (status === 400) return "Validation error — check your input.";
  }
  return "Something went wrong";
}
