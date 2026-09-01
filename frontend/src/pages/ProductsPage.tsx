import { useEffect, useState } from "react";
import { api, Product, Warehouse } from "../api";

type Modal =
  | { type: "price"; product: Product }
  | { type: "stock"; product: Product }
  | { type: "copy"; product: Product }
  | null;

function nextOfferId(offerId: string) {
  const stamp = new Date()
    .toISOString()
    .replace(/[-:TZ.]/g, "")
    .slice(0, 14);
  const suffix = `-${stamp}`;
  return `${offerId.slice(0, Math.max(1, 50 - suffix.length))}${suffix}`;
}

function colorClass(index: string) {
  const value = index.toUpperCase();
  if (value.includes("RED")) return "red";
  if (value.includes("YELLOW")) return "yellow";
  if (value.includes("SUPER")) return "super";
  if (value.includes("GREEN")) return "green";
  return "";
}

export default function ProductsPage() {
  const [items, setItems] = useState<Product[]>([]);
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [q, setQ] = useState("");
  const [color, setColor] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [modal, setModal] = useState<Modal>(null);
  const [price, setPrice] = useState("");
  const [oldPrice, setOldPrice] = useState("");
  const [stock, setStock] = useState("0");
  const [warehouseId, setWarehouseId] = useState("");
  const [offerId, setOfferId] = useState("");

  async function load() {
    const [products, houses] = await Promise.all([
      api.products({ q, color_index: color }),
      api.warehouses(),
    ]);
    setItems(products);
    setWarehouses(houses);
    if (!warehouseId && houses[0]) setWarehouseId(String(houses[0].warehouse_id));
  }

  useEffect(() => {
    load().catch((err: Error) => setError(err.message));
  }, []);

  async function run(action: () => Promise<unknown>) {
    setBusy(true);
    setError("");
    try {
      await action();
      await load();
      setModal(null);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section>
      <div className="page-head">
        <div>
          <h1>商品列表</h1>
          <p>共 {items.length} 条</p>
        </div>
        <div className="toolbar">
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="名称 / 货号" />
          <select value={color} onChange={(e) => setColor(e.target.value)}>
            <option value="">价格指数</option>
            <option value="GREEN">绿</option>
            <option value="YELLOW">黄</option>
            <option value="RED">红</option>
            <option value="SUPER">超值</option>
          </select>
          <button className="ghost" disabled={busy} onClick={() => run(load)}>筛选</button>
          <button className="btn" disabled={busy} onClick={() => run(api.syncProducts)}>从 Ozon 同步</button>
        </div>
      </div>
      {error && <div className="error">{error}</div>}
      <div className="panel">
        <table>
          <thead>
            <tr>
              <th>商品</th>
              <th>状态</th>
              <th>价格 / 指数</th>
              <th>库存</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.product_id} className={item.is_removed ? "removed" : undefined}>
                <td>
                  <div className="product">
                    {item.primary_image ? <img src={item.primary_image} alt="" /> : <span className="badge">无图</span>}
                    <div>
                      <div>{item.name || item.offer_id}</div>
                      <div className="muted">{item.offer_id} · ID {item.product_id}{item.sku ? ` · SKU ${item.sku}` : ""}</div>
                    </div>
                  </div>
                </td>
                <td>
                  <span className={`badge ${item.is_removed ? "red" : item.status_code === "IN_SALE" ? "sale" : item.is_archived ? "archived" : ""}`}>
                    {item.status_label}
                  </span>
                  {item.is_archived && item.status_code !== "ARCHIVED" && <span className="badge archived">已归档</span>}
                </td>
                <td>
                  <div>{item.price} {item.currency_code}</div>
                  <span className={`badge ${colorClass(item.color_index)}`}>{item.color_index_label || "无指数"}</span>
                  {item.ozon_min_price && <div className="muted">站内最低 {item.ozon_min_price}</div>}
                </td>
                <td>{item.stock_present} / 预留 {item.stock_reserved}</td>
                <td>
                  <div className="actions">
                    <button className="ghost" onClick={() => { setModal({ type: "price", product: item }); setPrice(item.price); setOldPrice(item.old_price); }}>改价</button>
                    <button className="ghost" onClick={() => { setModal({ type: "stock", product: item }); setStock(String(item.stock_present)); }}>库存</button>
                    <button
                      className={item.is_removed ? "btn" : "ghost"}
                      onClick={() => { setModal({ type: "copy", product: item }); setOfferId(nextOfferId(item.offer_id)); setPrice(item.price); }}
                    >
                      复制
                    </button>
                    <button className="ghost" onClick={() => run(() => api.archive([item.product_id], !item.is_archived))}>
                      {item.is_archived ? "恢复" : "归档"}
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {items.length === 0 && <div className="empty">还没有商品。先去设置里填 Client-Id，再点同步。</div>}
      </div>

      {modal && (
        <div className="modal-backdrop" onClick={() => setModal(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            {modal.type === "price" && (
              <>
                <h2>调整价格</h2>
                <div className="form-grid">
                  <label>售价<input value={price} onChange={(e) => setPrice(e.target.value)} /></label>
                  <label>划线价<input value={oldPrice} onChange={(e) => setOldPrice(e.target.value)} /></label>
                  <div className="actions">
                    <button className="btn" disabled={busy} onClick={() => run(() => api.updatePrice({ product_id: modal.product.product_id, price, old_price: oldPrice || undefined }))}>保存</button>
                    <button className="ghost" onClick={() => setModal(null)}>取消</button>
                  </div>
                </div>
              </>
            )}
            {modal.type === "stock" && (
              <>
                <h2>调整库存</h2>
                <div className="form-grid">
                  <label>
                    仓库
                    <select value={warehouseId} onChange={(e) => setWarehouseId(e.target.value)}>
                      {warehouses.map((house) => (
                        <option key={house.warehouse_id} value={house.warehouse_id}>{house.name}</option>
                      ))}
                    </select>
                  </label>
                  <label>数量<input value={stock} onChange={(e) => setStock(e.target.value)} /></label>
                  <div className="actions">
                    <button
                      className="btn"
                      disabled={busy || !warehouseId}
                      onClick={() => run(() => api.updateStock({
                        product_id: modal.product.product_id,
                        warehouse_id: Number(warehouseId),
                        stock: Number(stock),
                        offer_id: modal.product.offer_id,
                      }))}
                    >保存</button>
                    <button className="ghost" onClick={() => setModal(null)}>取消</button>
                  </div>
                </div>
              </>
            )}
            {modal.type === "copy" && (
              <>
                <h2>复制商品</h2>
                <p className="muted">
                  用本地快照新建卡片，并在描述末尾加上短混淆串。若原商品已下架，接口成功后会立刻归档原卡，避免再点一次又复制出重复品。
                </p>
                <div className="form-grid">
                  <label>新货号<input value={offerId} onChange={(e) => setOfferId(e.target.value)} /></label>
                  <label>价格<input value={price} onChange={(e) => setPrice(e.target.value)} /></label>
                  <div className="actions">
                    <button className="btn" disabled={busy} onClick={() => run(() => api.copyProduct(modal.product.product_id, { new_offer_id: offerId, price }))}>
                      提交复制
                    </button>
                    <button className="ghost" onClick={() => setModal(null)}>取消</button>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
