export type OrderStatusUi = "processing" | "success" | "failed" | "neutral";

export function mapOrderStatus(status: string): {
  label: string;
  ui: OrderStatusUi;
  className: string;
} {
  const s = status.toLowerCase();
  switch (s) {
    case "pending_payment":
      return {
        label: "Processing payment",
        ui: "processing",
        className:
          "bg-amber-100 text-amber-900 dark:bg-amber-900/40 dark:text-amber-100",
      };
    case "paid":
      return {
        label: "Paid",
        ui: "success",
        className:
          "bg-emerald-100 text-emerald-900 dark:bg-emerald-900/40 dark:text-emerald-100",
      };
    case "payment_failed":
      return {
        label: "Payment failed",
        ui: "failed",
        className: "bg-rose-100 text-rose-900 dark:bg-rose-900/40 dark:text-rose-100",
      };
    default:
      return {
        label: status,
        ui: "neutral",
        className: "bg-slate-200 text-slate-800 dark:bg-slate-700 dark:text-slate-100",
      };
  }
}
