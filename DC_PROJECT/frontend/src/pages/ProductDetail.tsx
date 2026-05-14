import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, getErrorMessage } from "../services/api";
import type { OrderRow, Product } from "../types";

export function ProductDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [product, setProduct] = useState<Product | null>(null);
  const [qty, setQty] = useState(1);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [placed, setPlaced] = useState<OrderRow | null>(null);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    (async () => {
      setLoading(true);
      setErr(null);
      try {
        const { data } = await api.get<Product>(`/products/${id}`);
        if (!cancelled) setProduct(data);
      } catch (e) {
        if (!cancelled) setErr(getErrorMessage(e));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id]);

  async function onOrder(e: FormEvent) {
    e.preventDefault();
    if (!id) return;
    setSubmitting(true);
    setErr(null);
    try {
      const { data } = await api.post<OrderRow>("/orders", {
        product_id: id,
        quantity: qty,
      });
      setPlaced(data);
      setTimeout(() => navigate("/orders"), 1200);
    } catch (e) {
      setErr(getErrorMessage(e));
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center py-24">
        <div className="h-10 w-10 animate-spin rounded-full border-2 border-indigo-600 border-t-transparent" />
      </div>
    );
  }

  if (err && !product) {
    return (
      <div className="rounded-lg border border-rose-200 bg-rose-50 p-6 text-rose-800 dark:border-rose-900 dark:bg-rose-950/40 dark:text-rose-100">
        {err}{" "}
        <Link to="/products" className="font-medium underline">
          Back to products
        </Link>
      </div>
    );
  }

  if (!product) return null;
const productImages: Record<string, string> = {
  camera: "/images/camera.jpg",
  keyboard: "/images/keyboard.jpg",
  watch: "/images/watch.jpg",
  phone: "/images/phone.jpg",
  headphones: "/images/headphone.jpg",
};

const productImage =
  productImages[product.name.toLowerCase()] ||
  "/images/phone.jpg";


  const maxQty = Math.max(1, product.stock);

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <Link to="/products" className="text-sm font-medium text-indigo-600 dark:text-indigo-400">
        ← All products
      </Link>

      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900">
       <img
          src={productImage}
          alt={product.name}
          className="h-72 w-full object-cover"
        />
        <div className="p-6">
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">{product.name}</h1>
          {product.category && (
            <p className="mt-1 text-sm text-slate-500">Category: {product.category}</p>
          )}
          <p className="mt-4 text-slate-600 dark:text-slate-300">{product.description}</p>
          {product.tags && product.tags.length > 0 && (
            <div className="mt-4 flex flex-wrap gap-2">
              {product.tags.map((t) => (
                <span
                  key={t}
                  className="rounded-full bg-slate-100 px-3 py-0.5 text-xs font-medium text-slate-700 dark:bg-slate-800 dark:text-slate-200"
                >
                  {t}
                </span>
              ))}
            </div>
          )}
          <div className="mt-6 flex flex-wrap items-baseline gap-4">
            <span className="text-3xl font-bold text-indigo-600 dark:text-indigo-400">
              ${product.price.toFixed(2)}
            </span>
            <span className="text-sm text-slate-500">{product.stock} available</span>
          </div>

          <form onSubmit={onOrder} className="mt-8 border-t border-slate-200 pt-6 dark:border-slate-800">
            <h2 className="font-semibold text-slate-900 dark:text-white">Place order</h2>
            <p className="mt-1 text-sm text-slate-500">
              Creates order with status <strong>pending_payment</strong>; payment runs asynchronously.
            </p>
            {err && (
              <div className="mt-4 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800 dark:border-rose-900 dark:bg-rose-950/40">
                {err}
              </div>
            )}
            {placed && (
              <div className="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-900 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-100">
                Order #{placed.id} created — redirecting to orders…
              </div>
            )}
            <div className="mt-4 flex flex-wrap items-end gap-4">
              <div>
                <label htmlFor="qty" className="block text-sm font-medium">
                  Quantity
                </label>
                <input
                  id="qty"
                  type="number"
                  min={1}
                  max={maxQty}
                  value={Math.min(qty, maxQty)}
                  onChange={(e) => setQty(Math.max(1, Number(e.target.value)))}
                  className="mt-1 w-28 rounded-lg border border-slate-300 px-3 py-2 dark:border-slate-600 dark:bg-slate-950 dark:text-white"
                />
              </div>
              <button
                type="submit"
                disabled={submitting || product.stock < 1}
                className="rounded-lg bg-indigo-600 px-6 py-2.5 font-semibold text-white shadow hover:bg-indigo-500 disabled:opacity-50"
              >
                {submitting ? "Submitting…" : "Order now"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
