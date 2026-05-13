import axios, { AxiosError } from "axios";

// 🚨 IMPORTANT: NO /api HERE
const baseURL =
  import.meta.env.VITE_API_URL?.replace(/\/$/, "") ||
  "https://dc-project-production-dc01.up.railway.app";

export const api = axios.create({
  baseURL,
  headers: { "Content-Type": "application/json" },
});

// ---------------- TOKEN ATTACH ----------------
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

// ---------------- ERROR HANDLING ----------------
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("access_token");

      const path = window.location.pathname;

      if (!path.startsWith("/login") && !path.startsWith("/register")) {
        window.location.href = "/login";
      }
    }

    return Promise.reject(error);
  }
);

// ---------------- ERROR HELPER ----------------
export function getErrorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const status = err.response?.status;
    const data: any = err.response?.data;

    if (data?.detail) {
      return typeof data.detail === "string"
        ? data.detail
        : JSON.stringify(data.detail);
    }

    if (status === 500) return "Server error";
    if (status === 400) return "Validation error";
  }

  return "Something went wrong";
}