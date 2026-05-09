import { FormEvent, useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../store/AuthContext";
import { getErrorMessage } from "../services/api";

export function Login() {
  const navigate = useNavigate();
  const { login, user, error, clearError } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [localErr, setLocalErr] = useState<string | null>(null);

  if (user) {
    return <Navigate to="/" replace />;
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setLocalErr(null);
    clearError();
    try {
      await login(email.trim(), password);
      navigate("/", { replace: true });
    } catch (err) {
      setLocalErr(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  const displayErr = localErr ?? error;

  return (
    <div className="mx-auto max-w-md">
      <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Login</h1>
      <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
        Use the email and password you registered with.
      </p>

      <form onSubmit={onSubmit} className="mt-8 space-y-4">
        {displayErr && (
          <div
            className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800 dark:border-rose-800 dark:bg-rose-950/50 dark:text-rose-200"
            role="alert"
          >
            {displayErr}
          </div>
        )}
        <div>
          <label htmlFor="email" className="block text-sm font-medium">
            Email
          </label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 dark:border-slate-600 dark:bg-slate-900 dark:text-white"
          />
        </div>
        <div>
          <label htmlFor="password" className="block text-sm font-medium">
            Password
          </label>
          <input
            id="password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 dark:border-slate-600 dark:bg-slate-900 dark:text-white"
          />
        </div>
        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-lg bg-indigo-600 py-2.5 text-sm font-semibold text-white shadow hover:bg-indigo-500 disabled:opacity-60"
        >
          {submitting ? "Signing in…" : "Sign in"}
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-slate-600 dark:text-slate-400">
        No account?{" "}
        <Link to="/register" className="font-medium text-indigo-600 dark:text-indigo-400">
          Register
        </Link>
      </p>
    </div>
  );
}
