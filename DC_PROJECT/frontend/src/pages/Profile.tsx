import { useEffect } from "react";
import { useAuth } from "../store/AuthContext";

export function Profile() {
  const { user, refreshUser } = useAuth();

  useEffect(() => {
    refreshUser().catch(() => {});
  }, [refreshUser]);

  if (!user) return null;

  return (
    <div className="mx-auto max-w-lg">
      <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Profile</h1>
      <dl className="mt-8 divide-y divide-slate-200 rounded-xl border border-slate-200 bg-white dark:divide-slate-800 dark:border-slate-800 dark:bg-slate-900">
        <div className="grid grid-cols-3 gap-2 px-4 py-3">
          <dt className="text-sm text-slate-500">Name</dt>
          <dd className="col-span-2 font-medium">{user.name}</dd>
        </div>
        <div className="grid grid-cols-3 gap-2 px-4 py-3">
          <dt className="text-sm text-slate-500">Email</dt>
          <dd className="col-span-2 font-medium">{user.email}</dd>
        </div>
        <div className="grid grid-cols-3 gap-2 px-4 py-3">
          <dt className="text-sm text-slate-500">Role</dt>
          <dd className="col-span-2 font-medium capitalize">{user.role}</dd>
        </div>
        <div className="grid grid-cols-3 gap-2 px-4 py-3">
          <dt className="text-sm text-slate-500">User ID</dt>
          <dd className="col-span-2 font-mono text-sm">{user.user_id}</dd>
        </div>
      </dl>
    </div>
  );
}
