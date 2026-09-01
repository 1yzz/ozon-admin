import { showToast } from "./toast";

function detailMessage(detail: unknown, fallback: string): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => (typeof item === "string" ? item : item?.msg || JSON.stringify(item)))
      .filter(Boolean)
      .join("；");
  }
  if (detail && typeof detail === "object") {
    const record = detail as { msg?: string; message?: string };
    return record.msg || record.message || JSON.stringify(detail);
  }
  return fallback;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  try {
    const response = await fetch(path, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers || {}),
      },
    });
    const text = await response.text();
    const data = text ? JSON.parse(text) : null;
    if (!response.ok) {
      const message = detailMessage(data?.detail, data ? JSON.stringify(data) : response.statusText);
      showToast("error", message);
      throw Object.assign(new Error(message), { toasted: true });
    }
    return data as T;
  } catch (err) {
    if ((err as { toasted?: boolean }).toasted) throw err;
    const message = err instanceof Error ? err.message : "网络请求失败";
    showToast("error", message);
    throw err instanceof Error ? err : new Error(message);
  }
}

export type Product = {
  product_id: number;
  offer_id: string;
  sku: number | null;
  name: string;
  status: string;
  status_name: string;
  status_description: string;
  is_archived: boolean;
  price: string;
  old_price: string;
  min_price: string;
  vat: string;
  currency_code: string;
  color_index: string;
  ozon_min_price: string;
  external_min_price: string;
  has_stock: boolean;
  stock_present: number;
  stock_reserved: number;
  primary_image: string;
  description_category_id: number | null;
  type_id: number | null;
  synced_at: string | null;
  has_snapshot: boolean;
  status_code: string;
  status_label: string;
  is_removed: boolean;
  color_index_label: string;
};

export type Warehouse = {
  warehouse_id: number;
  name: string;
  status: string;
  warehouse_type: string;
  is_rfbs: boolean;
  address: string;
};

export type Page<T> = {
  page: number;
  page_size: number;
  total: number;
  items: T[];
};

export type Order = {
  posting_number: string;
  order_number: string;
  order_id: number | null;
  status: string;
  substatus: string;
  in_process_at: string;
  shipment_date: string;
  delivering_date: string;
  warehouse_name: string;
  products: { name: string; offer_id: string; sku: number | null; quantity: number; price: string }[];
  cancel_reason: string;
  cancel_reason_id: number | null;
  cancellation_initiator: string;
  cancellation_type: string;
  cancelled_after_ship: boolean;
};

export type ReturnItem = {
  id: number;
  type: string;
  type_label: string;
  mode: string;
  status: string;
  status_sys: string;
  status_at: string;
  posting_number: string;
  order_number: string;
  order_id: number | null;
  reason: string;
  product_name: string;
  offer_id: string;
  sku: number | null;
  quantity: number;
  price: string;
  currency_code: string;
  place_name: string;
  target_place: string;
  return_date: string;
};

export type Settings = {
  client_id: string;
  api_key_masked: string;
  configured: boolean;
  connected: boolean | null;
  company_name: string;
  message: string;
};

export type Dashboard = {
  product_total: number;
  in_sale: number;
  archived: number;
  removed: number;
  red_price: number;
  yellow_price: number;
  empty_stock: number;
  warehouse_count: number;
  last_sync: string | null;
};

export type RepublishJob = {
  id: number;
  source_product_id: number;
  source_offer_id: string;
  new_offer_id: string;
  strategy: string;
  task_id: number | null;
  status: string;
  message: string;
  created_at: string;
};

export type CategoryNode = {
  description_category_id: number | null;
  category_name: string | null;
  type_id: number | null;
  type_name: string | null;
  disabled: boolean;
  children?: CategoryNode[];
};

export type CategoryAttribute = {
  id: number;
  name: string;
  description: string;
  is_required: boolean;
  type: string;
  dictionary_id: number;
  group_name: string;
  is_aspect: boolean;
};

export const api = {
  health: () => request<{ ok: boolean }>("/api/health"),
  dashboard: () => request<Dashboard>("/api/dashboard"),
  settings: () => request<Settings>("/api/settings"),
  saveSettings: (body: { client_id: string; api_key?: string }) =>
    request<Settings>("/api/settings", { method: "PUT", body: JSON.stringify(body) }),
  testSettings: () => request<Settings>("/api/settings/test", { method: "POST" }),
  products: (params: { q?: string; visibility?: string; color_index?: string } = {}) => {
    const search = new URLSearchParams();
    if (params.q) search.set("q", params.q);
    if (params.visibility) search.set("visibility", params.visibility);
    if (params.color_index) search.set("color_index", params.color_index);
    return request<Product[]>(`/api/products?${search.toString()}`);
  },
  syncProducts: () => request<{ synced: number }>("/api/products/sync", { method: "POST" }),
  archive: (productIds: number[], archive: boolean) =>
    request(`/api/products/${archive ? "archive" : "unarchive"}`, {
      method: "POST",
      body: JSON.stringify(productIds),
    }),
  updatePrice: (body: { product_id: number; price: string; old_price?: string; min_price?: string }) =>
    request("/api/products/price", { method: "POST", body: JSON.stringify(body) }),
  updateStock: (body: { product_id: number; warehouse_id: number; stock: number; offer_id?: string }) =>
    request("/api/products/stock", { method: "POST", body: JSON.stringify(body) }),
  copyProduct: (productId: number, body: { new_offer_id?: string; price?: string }) =>
    request(`/api/products/${productId}/copy`, { method: "POST", body: JSON.stringify(body) }),
  republish: (productId: number, body: { new_offer_id?: string; name?: string; price?: string }) =>
    request(`/api/products/${productId}/republish`, { method: "POST", body: JSON.stringify(body) }),
  createProduct: (body: Record<string, unknown>) =>
    request<{ task_id: number; name_ru: string; description_ru: string }>("/api/products/create", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  translateListing: (body: { name: string; description: string }) =>
    request<{ name_ru: string; description_ru: string }>("/api/products/translate", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  uploadImages: async (files: File[]) => {
    const form = new FormData();
    files.forEach((file) => form.append("files", file));
    const response = await fetch("/api/uploads/images", { method: "POST", body: form });
    const data = await response.json();
    if (!response.ok) {
      const message = typeof data?.detail === "string" ? data.detail : "图片上传失败";
      showToast("error", message);
      throw new Error(message);
    }
    return data as { items: { filename: string; url: string; original_name: string }[] };
  },
  categories: () => request<CategoryNode[]>("/api/products/meta/categories"),
  attributes: (descriptionCategoryId: number, typeId: number) =>
    request<CategoryAttribute[]>(
      `/api/products/meta/attributes?description_category_id=${descriptionCategoryId}&type_id=${typeId}`,
    ),
  jobs: () => request<RepublishJob[]>("/api/products/jobs/republish"),
  refreshJob: (jobId: number) => request(`/api/products/jobs/${jobId}/refresh`, { method: "POST" }),
  productStocks: (productId: number) =>
    request<{ warehouse_id: number; present: number; reserved: number; stock_type: string }[]>(
      `/api/products/${productId}/stocks`,
    ),
  warehouses: () => request<Warehouse[]>("/api/warehouses"),
  syncWarehouses: () => request<{ synced: number }>("/api/warehouses/sync", { method: "POST" }),
  orders: (params: { cancelled?: boolean; days?: number; page?: number; page_size?: number } = {}) => {
    const search = new URLSearchParams();
    search.set("cancelled", String(Boolean(params.cancelled)));
    search.set("days", String(params.days ?? 30));
    search.set("page", String(params.page ?? 1));
    search.set("page_size", String(params.page_size ?? 20));
    return request<Page<Order>>(`/api/orders?${search.toString()}`);
  },
  order: (postingNumber: string) => request<Order>(`/api/orders/${encodeURIComponent(postingNumber)}`),
  returns: (params: { days?: number; group?: string; page?: number; page_size?: number } = {}) => {
    const search = new URLSearchParams();
    search.set("days", String(params.days ?? 30));
    search.set("group", params.group || "all");
    search.set("page", String(params.page ?? 1));
    search.set("page_size", String(params.page_size ?? 20));
    search.set("schema", "FBS");
    return request<Page<ReturnItem>>(`/api/returns?${search.toString()}`);
  },
};
