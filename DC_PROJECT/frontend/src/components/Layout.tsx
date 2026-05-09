import { Link, NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../store/AuthContext";
import { useEffect, useState } from "react";

export function Layout() {
  const { user, logout } = useAuth();
  const [dark, setDark] = useState(() =>
    document.documentElement.classList.contains("dark"),
  );

  useEffect(() => {
    if (dark) document.documentElement.classList.add("dark");
    else document.documentElement.classList.remove("dark");
    localStorage.setItem("theme", dark ? "dark" : "light");
  }, [dark]);

  useEffect(() => {
    const saved = localStorage.getItem("theme");
    if (saved === "dark") setDark(true);
  }, []);

  const navCls = ({ isActive }: { isActive: boolean }) =>
    `rounded-md px-3 py-2 text-sm font-medium transition ${
      isActive
        ? "bg-indigo-600 text-white"
        : "text-slate-700 hover:bg-slate-200 dark:text-slate-200 dark:hover:bg-slate-800"
    }`;

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-slate-200 bg-white/90 backdrop-blur dark:border-slate-800 dark:bg-slate-900/90 sticky top-0 z-40">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-4 py-3">
          <Link to="/" className="text-lg font-semibold tracking-tight text-indigo-600 dark:text-indigo-400">
            Distributed Commerce
          </Link>
          <nav className="flex flex-wrap items-center gap-1">
            <NavLink to="/" end className={navCls}>
              Home
            </NavLink>
            <NavLink to="/products" className={navCls}>
              Products
            </NavLink>
            {user && (
              <>
                <NavLink to="/orders" className={navCls}>
                  Orders
                </NavLink>
                <NavLink to="/profile" className={navCls}>
                  Profile
                </NavLink>
                {user.role === "admin" && (
                  <NavLink to="/admin" className={navCls}>
                    Admin
                  </NavLink>
                )}
              </>
            )}
          </nav>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setDark((d) => !d)}
              className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium dark:border-slate-600"
              aria-label="Toggle dark mode"
            >
              {dark ? "Light" : "Dark"}
            </button>
            {user ? (
              <div className="flex items-center gap-2 text-sm">
                <span className="hidden sm:inline text-slate-600 dark:text-slate-400">
                  {user.name}
                </span>
                <button
                  type="button"
                  onClick={logout}
                  className="rounded-md bg-slate-200 px-3 py-1.5 font-medium dark:bg-slate-700"
                >
                  Log out
                </button>
              </div>
            ) : (
              <div className="flex gap-2">
                <Link
                  to="/login"
                  className="rounded-md px-3 py-1.5 text-sm font-medium text-indigo-600 dark:text-indigo-400"
                >
                  Login
                </Link>
                <Link
                  to="/register"
                  className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white"
                >
                  Register
                </Link>
              </div>
            )}
          </div>
        </div>
      </header>
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-8">
        <Outlet />
      </main>
      <footer className="mt-16 border-t border-slate-200 bg-white py-10 text-center dark:border-slate-800 dark:bg-slate-900">
  <h3 className="text-lg font-bold text-indigo-600">
    Distributed E-Commerce System
  </h3>

  <p className="mt-2 text-sm text-slate-500">
    CS-432 Distributed Computing Project
  </p>

  <p className="mt-1 text-sm text-slate-500">
    Built with React, Docker, RabbitMQ, Redis, MongoDB, and MySQL.
  </p>
</footer>
    </div>
  );
}
