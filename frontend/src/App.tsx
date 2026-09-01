import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import ToastHost from "./ToastHost";
import DashboardPage from "./pages/DashboardPage";
import OrdersPage from "./pages/OrdersPage";
import ReturnsPage from "./pages/ReturnsPage";
import ProductCreatePage from "./pages/ProductCreatePage";
import ProductsPage from "./pages/ProductsPage";
import RepublishPage from "./pages/RepublishPage";
import SettingsPage from "./pages/SettingsPage";
import WarehousesPage from "./pages/WarehousesPage";

const links = [
  { to: "/", label: "工作台" },
  { to: "/products", label: "商品" },
  { to: "/products/new", label: "新上架" },
  { to: "/republish", label: "复刊中心" },
  { to: "/orders", label: "订单" },
  { to: "/returns", label: "退货和取消" },
  { to: "/warehouses", label: "仓库" },
  { to: "/settings", label: "设置" },
];

export default function App() {
  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          OZON ADMIN
          <small>FBS 单店后台</small>
        </div>
        <nav className="nav">
          {links.map((link) => (
            <NavLink key={link.to} to={link.to} end={link.to === "/"}>
              {link.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <ToastHost />
      <main className="main">
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/products" element={<ProductsPage />} />
          <Route path="/products/new" element={<ProductCreatePage />} />
          <Route path="/republish" element={<RepublishPage />} />
          <Route path="/orders" element={<OrdersPage />} />
          <Route path="/returns" element={<ReturnsPage />} />
          <Route path="/warehouses" element={<WarehousesPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}
