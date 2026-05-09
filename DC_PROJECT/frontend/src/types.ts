export interface UserMe {
  user_id: number;
  email: string;
  role: string;
  name: string;
}

export interface Product {
  id: string;
  name: string;
  description: string;
  price: number;
  stock: number;
  category?: string | null;
  tags?: string[] | null;
  image?: string;
}

export interface PaginatedProducts {
  items: Product[];
  total: number;
  page: number;
  limit: number;
}

export interface OrderRow {
  id: number;
  user_id: number;
  product_id: string;
  quantity: number;
  total_price: number;
  status: string;
  transaction_id: string | null;
  created_at: string;
}
