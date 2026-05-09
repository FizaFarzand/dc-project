import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { api, getErrorMessage } from "../services/api";
import type { OrderRow, PaginatedProducts, Product } from "../types";
import { mapOrderStatus } from "../utils/orderStatus";

type Tab = "dashboard" | "products" | "orders";

interface AdminUser {
  id: number;
  name: string;
  email: string;
  role: string;
}

export function AdminPanel() {
  const [tab, setTab] = useState<Tab>("dashboard");
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [productPage, setProductPage] = useState<PaginatedProducts | null>(null);
  const [orders, setOrders] = useState<OrderRow[]>([]);
  const [productsMap, setProductsMap] = useState<Record<string, Product>>({});
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  const [form, setForm] = useState({
    name: "",
    description: "",
    price: "",
    stock: "",
    category: "",
    tags: "",
  });
  const [editingId, setEditingId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const loadDashboard = useCallback(async () => {
    setErr(null);
    setLoading(true);
    try {
      const [uRes, pRes, oRes] = await Promise.all([
        api.get<AdminUser[]>("/users"),
        api.get<PaginatedProducts>("/products", { params: { page: 1, limit: 500 } }),
        api.get<OrderRow[]>("/orders"),
      ]);
      setUsers(uRes.data);
      setProductPage(pRes.data);
      setOrders(oRes.data);
    } catch (e) {
      setErr(getErrorMessage(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadDashboard();
  }, [loadDashboard]);

  useEffect(() => {
    if (!orders.length) return;
    const ids = [...new Set(orders.map((o) => o.product_id))];
    let cancelled = false;
    (async () => {
      const rows = await Promise.all(
        ids.map(async (id) => {
          try {
            const { data } = await api.get<Product>(`/products/${id}`);
            return [id, data] as const;
          } catch {
            return [id, null] as const;
          }
        }),
      );
      if (cancelled) return;
      setProductsMap((prev) => {
        const n = { ...prev };
        for (const [id, p] of rows) if (p) n[id] = p;
        return n;
      });
    })();
    return () => {
      cancelled = true;
    };
  }, [orders]);

  const dashboardStats = useMemo(() => {
    const paid = orders.filter((o) => o.status === "paid").length;
    const failed = orders.filter((o) => o.status === "payment_failed").length;
    const pending = orders.filter((o) => o.status === "pending_payment").length;
    const attempted = paid + failed;
    const ratio = attempted ? Math.round((paid / attempted) * 100) : 0;
    return {
      users: users.length,
      products: productPage?.total ?? 0,
      orders: orders.length,
      paid,
      failed,
      pending,
      successRatio: ratio,
    };
  }, [users, productPage, orders]);

  async function refreshProductsOnly() {
    try {
      const { data } = await api.get<PaginatedProducts>("/products", {
        params: { page: 1, limit: 500 },
      });
      setProductPage(data);
    } catch (e) {
      setErr(getErrorMessage(e));
    }
  }

  async function refreshOrdersOnly() {
    try {
      const { data } = await api.get<OrderRow[]>("/orders");
      setOrders(data);
    } catch (e) {
      setErr(getErrorMessage(e));
    }
  }

  function startEdit(p: Product) {
    setEditingId(p.id);
    setForm({
      name: p.name,
      description: p.description,
      price: String(p.price),
      stock: String(p.stock),
      category: p.category ?? "",
      tags: p.tags?.join(", ") ?? "",
    });
  }

  function resetForm() {
    setEditingId(null);
    setForm({
      name: "",
      description: "",
      price: "",
      stock: "",
      category: "",
      tags: "",
    });
  }

  async function onSubmitProduct(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setErr(null);
    const price = Number(form.price);
    const stock = Number(form.stock);
    const tags = form.tags
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);
    const body = {
      name: form.name.trim(),
      description: form.description.trim(),
      price,
      stock,
      category: form.category.trim() || undefined,
      tags: tags.length ? tags : undefined,
    };
    try {
      if (editingId) {
        await api.put(`/products/${editingId}`, body);
      } else {
        await api.post("/products", body);
      }
      resetForm();
      await refreshProductsOnly();
      await loadDashboard();
    } catch (e) {
      setErr(getErrorMessage(e));
    } finally {
      setSubmitting(false);
    }
  }

  async function deleteProduct(id: string) {
    if (!window.confirm("Delete this product?")) return;
    setErr(null);
    try {
      await api.delete(`/products/${id}`);
      await refreshProductsOnly();
    } catch (e) {
      setErr(getErrorMessage(e));
    }
  }

  async function patchOrderStatus(orderId: number, status: string) {
    setErr(null);
    try {
      await api.patch(`/orders/${orderId}/status`, { status });
      await refreshOrdersOnly();
    } catch (e) {
      setErr(getErrorMessage(e));
    }
  }

  const statusOptions = [
    "pending_payment",
    "paid",
    "payment_failed",
    "cancelled",
    "created",
  ];

  const items = productPage?.items ?? [];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Admin panel</h1>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
          Manage catalog and orders · requires admin role in JWT.
        </p>
      </div>

      <div className="flex flex-wrap gap-2 border-b border-slate-200 pb-3 dark:border-slate-800">
        {(
          [
            ["dashboard", "Dashboard"],
            ["products", "Products"],
            ["orders", "Orders"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            onClick={() => setTab(id)}
            className={`rounded-lg px-4 py-2 text-sm font-medium ${
              tab === id
                ? "bg-indigo-600 text-white"
                : "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {err && (
        <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800 dark:border-rose-900 dark:bg-rose-950/40">
          {err}
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-16">
          <div className="h-10 w-10 animate-spin rounded-full border-2 border-indigo-600 border-t-transparent" />
        </div>
      ) : (
        <>
          {tab === "dashboard" && (
  <div className="space-y-8">
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <StatCard label="Total users" value={dashboardStats.users} />
      <StatCard label="Total products" value={dashboardStats.products} />
      <StatCard label="Total orders" value={dashboardStats.orders} />
      <StatCard
        label="Paid / failed (attempts)"
        value={`${dashboardStats.paid} / ${dashboardStats.failed}`}
        sub={`${dashboardStats.successRatio}% success rate (paid vs paid+failed)`}
      />
    </div>

    <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800">
      <table className="min-w-full divide-y divide-slate-200 text-sm dark:divide-slate-800">
        <thead className="bg-slate-50 dark:bg-slate-900/80">
          <tr>
            <th className="px-4 py-3 text-left font-semibold">User</th>
            <th className="px-4 py-3 text-left font-semibold">Email</th>
            <th className="px-4 py-3 text-left font-semibold">Role</th>
            <th className="px-4 py-3 text-left font-semibold">Shopping Details</th>
          </tr>
        </thead>

        <tbody className="divide-y divide-slate-200 bg-white dark:divide-slate-800 dark:bg-slate-950/40">
          {users.map((user) => {
            const userOrders = orders.filter(
              (o) => Number(o.user_id) === Number(user.id),
            );

            return (
              <tr key={user.id}>
                <td className="px-4 py-3">{user.name}</td>

                <td className="px-4 py-3">{user.email}</td>

                <td className="px-4 py-3">{user.role}</td>

                <td className="px-4 py-3">
                  {userOrders.length === 0 ? (
                    <span className="text-slate-400">No orders</span>
                  ) : (
                    <div className="space-y-3">
                      {userOrders.map((order) => {
                        const product = productsMap[order.product_id];

                        return (
                          <div
                            key={order.id}
                            className="rounded-lg border border-slate-200 p-3 dark:border-slate-700"
                          >
                            <p>
                              <strong>Order:</strong> #{order.id}
                            </p>

                            <p>
                              <strong>Product:</strong>{" "}
                              {product?.name ?? "Deleted Product"}
                            </p>

                            <p>
                              <strong>Quantity:</strong> {order.quantity}
                            </p>

                            <p>
                              <strong>Total:</strong> $
                              {order.total_price.toFixed(2)}
                            </p>

                            <p>
                              <strong>Status:</strong> {order.status}
                            </p>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  </div>
)}

          {tab === "products" && (
            <div className="space-y-8">
              <form
                onSubmit={onSubmitProduct}
                className="rounded-xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900"
              >
                <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
                  {editingId ? "Edit product" : "Create product"}
                </h2>
                <div className="mt-4 grid gap-4 sm:grid-cols-2">
                  <Field
                    label="Name"
                    value={form.name}
                    onChange={(v) => setForm((f) => ({ ...f, name: v }))}
                    required
                  />
                  <Field
                    label="Category"
                    value={form.category}
                    onChange={(v) => setForm((f) => ({ ...f, category: v }))}
                  />
                  <Field
                    label="Price"
                    type="number"
                    step="0.01"
                    value={form.price}
                    onChange={(v) => setForm((f) => ({ ...f, price: v }))}
                    required
                  />
                  <Field
                    label="Stock"
                    type="number"
                    value={form.stock}
                    onChange={(v) => setForm((f) => ({ ...f, stock: v }))}
                    required
                  />
                  <div className="sm:col-span-2">
                    <label className="block text-sm font-medium">Description</label>
                    <textarea
                      required
                      rows={3}
                      value={form.description}
                      onChange={(e) =>
                        setForm((f) => ({ ...f, description: e.target.value }))
                      }
                      className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 dark:border-slate-600 dark:bg-slate-950"
                    />
                  </div>
                  <div className="sm:col-span-2">
                    <label className="block text-sm font-medium">Tags (comma-separated)</label>
                    <input
                      value={form.tags}
                      onChange={(e) => setForm((f) => ({ ...f, tags: e.target.value }))}
                      className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 dark:border-slate-600 dark:bg-slate-950"
                      placeholder="e.g. electronics, sale"
                    />
                  </div>
                </div>
                <div className="mt-4 flex gap-2">
                  <button
                    type="submit"
                    disabled={submitting}
                    className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
                  >
                    {submitting ? "Saving…" : editingId ? "Update" : "Create"}
                  </button>
                  {editingId && (
                    <button
                      type="button"
                      onClick={resetForm}
                      className="rounded-lg border border-slate-300 px-4 py-2 text-sm dark:border-slate-600"
                    >
                      Cancel edit
                    </button>
                  )}
                </div>
              </form>

              <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800">
                <table className="min-w-full divide-y divide-slate-200 text-sm dark:divide-slate-800">
                  <thead className="bg-slate-50 dark:bg-slate-900/80">
                    <tr>
                      <th className="px-4 py-3 text-left font-semibold">Name</th>
                      <th className="px-4 py-3 text-right font-semibold">Price</th>
                      <th className="px-4 py-3 text-right font-semibold">Stock</th>
                      <th className="px-4 py-3 text-right font-semibold">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200 bg-white dark:divide-slate-800 dark:bg-slate-950/40">
                    {items.map((p) => (
                      <tr key={p.id}>
                        <td className="px-4 py-3">{p.name}</td>
                        <td className="px-4 py-3 text-right">${p.price.toFixed(2)}</td>
                        <td className="px-4 py-3 text-right">{p.stock}</td>
                        <td className="px-4 py-3 text-right">
                          <button
                            type="button"
                            onClick={() => startEdit(p)}
                            className="mr-2 text-indigo-600 dark:text-indigo-400"
                          >
                            Edit
                          </button>
                          <button
                            type="button"
                            onClick={() => void deleteProduct(p.id)}
                            className="text-rose-600"
                          >
                            Delete
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {tab === "orders" && (
            <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800">
              <table className="min-w-full divide-y divide-slate-200 text-sm dark:divide-slate-800">
                <thead className="bg-slate-50 dark:bg-slate-900/80">
                  <tr>
                    <th className="px-4 py-3 text-left font-semibold">Order</th>
                    <th className="px-4 py-3 text-left font-semibold">User</th>
                    <th className="px-4 py-3 text-left font-semibold">Product</th>
                    <th className="px-4 py-3 text-left font-semibold">Status</th>
                    <th className="px-4 py-3 text-left font-semibold">Set status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 bg-white dark:divide-slate-800 dark:bg-slate-950/40">
                  {orders.map((o) => {
                    const prod = productsMap[o.product_id];
                    const st = mapOrderStatus(o.status);
                    return (
                      <tr key={o.id}>
                        <td className="px-4 py-3 font-mono text-xs">#{o.id}</td>
                        <td className="px-4 py-3">{o.user_id}</td>
                        <td className="px-4 py-3">{prod?.name ?? o.product_id}</td>
                        <td className="px-4 py-3">
                          <span
                            className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ${st.className}`}
                          >
                            {st.label}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <select
                            defaultValue={o.status}
                            onChange={(e) =>
                              void patchOrderStatus(o.id, e.target.value)
                            }
                            className="rounded border border-slate-300 bg-white px-2 py-1 text-xs dark:border-slate-600 dark:bg-slate-900"
                          >
                            {statusOptions.map((s) => (
                              <option key={s} value={s}>
                                {s}
                              </option>
                            ))}
                          </select>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function StatCard({
  label,
  value,
  sub,
}: {
  label: string;
  value: string | number;
  sub?: string;
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-bold text-slate-900 dark:text-white">{value}</p>
      {sub && <p className="mt-1 text-xs text-slate-500">{sub}</p>}
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  type = "text",
  required,
  step,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
  required?: boolean;
  step?: string;
}) {
  return (
    <div>
      <label className="block text-sm font-medium">{label}</label>
      <input
        type={type}
        required={required}
        step={step}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 dark:border-slate-600 dark:bg-slate-950 dark:text-white"
      />
    </div>
  );
}
