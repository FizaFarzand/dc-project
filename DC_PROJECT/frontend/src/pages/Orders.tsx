import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, getErrorMessage } from "../services/api";
import type { OrderRow, Product } from "../types";
import { mapOrderStatus } from "../utils/orderStatus";

const POLL_MS = 2500;

export function Orders() {
  const [orders, setOrders] = useState<OrderRow[]>([]);
  const [products, setProducts] = useState<Record<string, Product>>({});
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const fetchedProductIds = useRef(new Set<string>());

  const loadOrders = useCallback(async () => {
  setErr(null);
  setLoading(true);

  try {
    const { data } = await api.get<OrderRow[]>("/orders", {
      params: {
        t: Date.now(),
      },
    });

    setOrders(data);
  } catch (e) {
    setErr(getErrorMessage(e));
  } finally {
    setLoading(false);
  }
}, []);
  useEffect(() => {
    void loadOrders();
  }, [loadOrders]);

  useEffect(() => {
    if (!orders.length) return;
    const ids = [...new Set(orders.map((o) => o.product_id))];
    const need = ids.filter((id) => !fetchedProductIds.current.has(id));
    if (!need.length) return;

    let cancelled = false;
    (async () => {
      const snapshots = await Promise.all(
        need.map(async (id) => {
          fetchedProductIds.current.add(id);
          try {
            const { data } = await api.get<Product>(`/products/${id}`);
            return [id, data] as const;
          } catch {
            fetchedProductIds.current.delete(id);
            return [id, null] as const;
          }
        }),
      );
      if (cancelled) return;
      setProducts((prev) => {
        const next = { ...prev };
        for (const [id, p] of snapshots) {
          if (p) next[id] = p;
        }
        return next;
      });
    })();

    return () => {
      cancelled = true;
    };
  }, [orders]);

  const needsPoll = useMemo(
    () => orders.some((o) => o.status === "pending_payment"),
    [orders],
  );

  useEffect(() => {
    if (!needsPoll) return;
    const id = window.setInterval(() => {
      void loadOrders();
    }, POLL_MS);
    return () => window.clearInterval(id);
  }, [needsPoll, loadOrders]);

  const stats = useMemo(() => {
    const total = orders.length;
    const paid = orders.filter((o) => o.status === "paid").length;
    const failed = orders.filter((o) => o.status === "payment_failed").length;
    return { total, paid, failed };
  }, [orders]);

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Orders</h1>
        </div>
        <button
          type="button"
          onClick={() => {
            console.log("REFRESH CLICKED");
            void loadOrders();
          }}
          className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium dark:border-slate-600"
        >
          Refresh now
        </button>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
          <p className="text-xs font-medium uppercase text-slate-500">Total orders</p>
          <p className="mt-1 text-2xl font-bold">{stats.total}</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
          <p className="text-xs font-medium uppercase text-slate-500">Paid</p>
          <p className="mt-1 text-2xl font-bold text-emerald-600">{stats.paid}</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
          <p className="text-xs font-medium uppercase text-slate-500">Failed</p>
          <p className="mt-1 text-2xl font-bold text-rose-600">{stats.failed}</p>
        </div>
      </div>

      {needsPoll && (
        <div className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-100">
          <span className="relative flex h-3 w-3">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-amber-400 opacity-75" />
            <span className="relative inline-flex h-3 w-3 rounded-full bg-amber-500" />
          </span>
          Processing payment… updating automatically.
        </div>
      )}

      {err && (
        <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800 dark:border-rose-900 dark:bg-rose-950/40">
          {err}
        </div>
      )}

      {loading && orders.length === 0 ? (
        <div className="flex justify-center py-16">
          <div className="h-10 w-10 animate-spin rounded-full border-2 border-indigo-600 border-t-transparent" />
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800">
          <table className="min-w-full divide-y divide-slate-200 text-sm dark:divide-slate-800">
            <thead className="bg-slate-50 dark:bg-slate-900/80">
              <tr>
                <th className="px-4 py-3 text-left font-semibold">Order</th>
                <th className="px-4 py-3 text-left font-semibold">Product</th>
                <th className="px-4 py-3 text-right font-semibold">Qty</th>
                <th className="px-4 py-3 text-right font-semibold">Total</th>
                <th className="px-4 py-3 text-left font-semibold">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 bg-white dark:divide-slate-800 dark:bg-slate-950/40">
              {orders.map((o) => {
                const prod = products[o.product_id];
                const st = mapOrderStatus(o.status);
                return (
                  <tr key={o.id}>
                    <td className="px-4 py-3 font-mono text-xs">#{o.id}</td>
                    <td className="px-4 py-3">
                      {prod?.name ?? (
                        <span className="text-slate-400">Product {o.product_id}</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">{o.quantity}</td>
                    <td className="px-4 py-3 text-right">${o.total_price.toFixed(2)}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold ${st.className}`}
                      >
                        {st.label}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {orders.length === 0 && (
            <p className="p-8 text-center text-sm text-slate-500">No orders yet.</p>
          )}
        </div>
      )}
    </div>
  );
}
