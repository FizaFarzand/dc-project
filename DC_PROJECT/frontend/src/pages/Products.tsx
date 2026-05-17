import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, getErrorMessage } from "../services/api";
import type { PaginatedProducts, Product } from "../types";
import { debounce } from "../utils/debounce";
import { LoadingSpinner } from "../components/Loading_Spinner";

const PAGE_SIZE = 12;

const productImages: Record<string, string> = {
  camera: "/images/camera.jpg",
  keyboard: "/images/keyboard.jpg",
  watch: "/images/watch.jpg",
  phone: "/images/phone.jpg",
  headphones: "/images/headphone.jpg",
  "gaming mouse": "/images/gaming-mouse.jpg",
  "bluetooth speaker": "/images/speaker.jpg",
  "laptop stand": "/images/laptop-stand.jpg",
  tablet: "/images/tablet.jpg",
  "smart tv": "/images/smart-tv.jpg",
};


export function Products() {
  const [browse, setBrowse] = useState<PaginatedProducts | null>(null);
  const [searchResults, setSearchResults] = useState<Product[] | null>(null);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  const [qInput, setQInput] = useState("");
  const [q, setQ] = useState("");
  const [category, setCategory] = useState("");
  const [tags, setTags] = useState("");

  const debouncedSetQ = useMemo(
    () =>
      debounce((value: string) => {
        setQ(value.trim());
      }, 350),
    [],
  );

  useEffect(() => {
    debouncedSetQ(qInput);
  }, [qInput, debouncedSetQ]);

  const searchMode = Boolean(q || category.trim() || tags.trim());

  const loadBrowse = useCallback(async () => {
    setLoading(true);
    setErr(null);

    try {
      const { data } = await api.get<PaginatedProducts>("/products", {
        params: { page, limit: PAGE_SIZE },
      });

      setBrowse(data);
      setSearchResults(null);
    } catch (e) {
      setErr(getErrorMessage(e));
    } finally {
      setLoading(false);
    }
  }, [page]);

  const loadSearch = useCallback(async () => {
    setLoading(true);
    setErr(null);

    try {
      const { data } = await api.get<Product[]>("/products/search", {
        params: {
          q: q || undefined,
          category: category.trim() || undefined,
          tags: tags.trim() || undefined,
        },
      });

      setSearchResults(data);
      setBrowse(null);
    } catch (e) {
      setErr(getErrorMessage(e));
    } finally {
      setLoading(false);
    }
  }, [q, category, tags]);

  useEffect(() => {
    if (!searchMode) {
      void loadBrowse();
    }
  }, [searchMode, loadBrowse]);

  useEffect(() => {
    if (searchMode) {
      void loadSearch();
    }
  }, [searchMode, loadSearch]);

  const items = searchMode ? searchResults ?? [] : browse?.items ?? [];

  const totalPages = browse
    ? Math.max(1, Math.ceil(browse.total / PAGE_SIZE))
    : 1;

  return (
    <div className="space-y-10">
      <div className="text-center">
        <h1 className="text-4xl font-extrabold text-slate-900 dark:text-white">
          Explore Our Products
        </h1>

        <p className="mt-3 text-slate-600 dark:text-slate-400">
          Browse our distributed e-commerce catalog powered by microservices,
          Docker, RabbitMQ, Redis, MongoDB, and MySQL.
        </p>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-lg dark:border-slate-800 dark:bg-slate-900">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="sm:col-span-2">
            <label className="block text-xs font-medium text-slate-500">
              Search
            </label>

            <input
              type="search"
              placeholder="Search products..."
              value={qInput}
              onChange={(e) => setQInput(e.target.value)}
              className="mt-1 w-full rounded-xl border border-slate-300 px-4 py-3 text-sm shadow-sm dark:border-slate-600 dark:bg-slate-950 dark:text-white"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-500">
              Category
            </label>

            <input
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              placeholder="Optional"
              className="mt-1 w-full rounded-xl border border-slate-300 px-4 py-3 text-sm shadow-sm dark:border-slate-600 dark:bg-slate-950 dark:text-white"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-500">
              Tags
            </label>

            <input
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              placeholder="comma, separated"
              className="mt-1 w-full rounded-xl border border-slate-300 px-4 py-3 text-sm shadow-sm dark:border-slate-600 dark:bg-slate-950 dark:text-white"
            />
          </div>
        </div>

        {(qInput || category || tags) && (
          <button
            type="button"
            onClick={() => {
              setQInput("");
              setCategory("");
              setTags("");
              setQ("");
              setPage(1);
            }}
            className="mt-4 rounded-lg bg-indigo-100 px-4 py-2 text-sm font-medium text-indigo-700 transition hover:bg-indigo-200 dark:bg-indigo-900 dark:text-indigo-200"
          >
            Clear Filters
          </button>
        )}
      </div>

      {err && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800 dark:border-rose-900 dark:bg-rose-950/40 dark:text-rose-100">
          {err}
        </div>
      )}

      {loading && <LoadingSpinner />}

      {!loading && (
        <>
          <p className="text-sm text-slate-600 dark:text-slate-400">
            {searchMode ? (
              <>
                {items.length} result{items.length === 1 ? "" : "s"} found
              </>
            ) : (
              <>
                Showing page {page} of {totalPages} (
                {browse?.total ?? 0} products)
              </>
            )}
          </p>

          <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-3">
            {items.map((p) => {
              const image =
                productImages[p.name.toLowerCase()] || "/images/phone.jpg";

              return (
                <article
                  key={p.id}
                  className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-lg transition hover:-translate-y-2 hover:shadow-2xl dark:border-slate-800 dark:bg-slate-900"
                >
                  <img
                    src={image}
                    alt={p.name}
                    className="h-64 w-full object-cover"
                  />

                  <div className="flex flex-1 flex-col p-6">
                    <h2 className="text-xl font-bold text-slate-900 dark:text-white">
                      {p.name}
                    </h2>

                    <p className="mt-2 line-clamp-2 text-sm text-slate-600 dark:text-slate-400">
                      {p.description}
                    </p>

                    <div className="mt-5 flex items-end justify-between">
                      <div>
                        <p className="text-2xl font-bold text-indigo-600 dark:text-indigo-400">
                          ${p.price.toFixed(2)}
                        </p>

                        <p className="mt-1 text-xs text-slate-500">
                          {p.stock} items available
                        </p>
                      </div>

                      <Link
                        to={`/products/${p.id}`}
                        className="rounded-xl bg-indigo-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-indigo-700"
                      >
                        View Details
                      </Link>
                    </div>
                  </div>
                </article>
              );
            })}
          </div>

          {!searchMode && browse && totalPages > 1 && (
            <div className="flex justify-center gap-4 pt-8">
              <button
                type="button"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="rounded-xl border border-slate-300 px-5 py-3 text-sm font-medium transition hover:bg-slate-100 disabled:opacity-40 dark:border-slate-600 dark:hover:bg-slate-800"
              >
                Previous
              </button>

              <button
                type="button"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
                className="rounded-xl border border-slate-300 px-5 py-3 text-sm font-medium transition hover:bg-slate-100 disabled:opacity-40 dark:border-slate-600 dark:hover:bg-slate-800"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}