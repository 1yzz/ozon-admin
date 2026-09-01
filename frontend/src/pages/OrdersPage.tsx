import { useEffect, useState } from "react";
import Pager from "../Pager";
import { api, Order } from "../api";

export default function OrdersPage() {
  const [tab, setTab] = useState<"all" | "cancelled">("all");
  const [items, setItems] = useState<Order[]>([]);
  const [days, setDays] = useState(30);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const pageSize = 20;
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [detail, setDetail] = useState<Order | null>(null);

  async function load(nextTab = tab, nextPage = page, nextDays = days) {
    setBusy(true);
    setError("");
    try {
      const result = await api.orders({
        cancelled: nextTab === "cancelled",
        days: nextDays,
        page: nextPage,
        page_size: pageSize,
      });
      setItems(result.items);
      setTotal(result.total);
      setPage(result.page);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    load("all", 1);
  }, []);

  function switchTab(next: "all" | "cancelled") {
    setTab(next);
    load(next, 1);
  }

  return (
    <section>
      <div className="page-head">
        <div>
          <h1>订单</h1>
          <p>只读查看 FBS 订单。已取消订单单独列出，并带上取消原因。</p>
        </div>
        <div className="toolbar">
          <select
            value={days}
            onChange={(e) => {
              const next = Number(e.target.value);
              setDays(next);
              load(tab, 1, next);
            }}
          >
            <option value={14}>近 14 天</option>
            <option value={30}>近 30 天</option>
            <option value={90}>近 90 天</option>
          </select>
          <button className="ghost" disabled={busy} onClick={() => load(tab, 1)}>刷新</button>
        </div>
      </div>
      <div className="tabs">
        <button className="ghost" aria-current={tab === "all"} onClick={() => switchTab("all")}>全部订单</button>
        <button className="ghost" aria-current={tab === "cancelled"} onClick={() => switchTab("cancelled")}>已取消</button>
      </div>
      {error && <div className="error">{error}</div>}
      <div className="panel">
        <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>发货单</th>
              <th>商品</th>
              <th>状态</th>
              {tab === "cancelled" && <th>取消原因</th>}
              <th>时间</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.posting_number} onClick={() => setDetail(item)} style={{ cursor: "pointer" }}>
                <td>
                  <div>{item.posting_number}</div>
                  <div className="muted">{item.order_number}</div>
                </td>
                <td>
                  {item.products.map((product) => (
                    <div key={`${product.offer_id}-${product.sku}`}>
                      {product.name} × {product.quantity}
                    </div>
                  ))}
                </td>
                <td>{item.status}{item.substatus ? ` / ${item.substatus}` : ""}</td>
                {tab === "cancelled" && (
                  <td>
                    <div>{item.cancel_reason || "未返回原因"}</div>
                    <div className="muted">
                      {item.cancellation_initiator}
                      {item.cancel_reason_id ? ` · #${item.cancel_reason_id}` : ""}
                    </div>
                  </td>
                )}
                <td>
                  <div>{item.in_process_at}</div>
                  <div className="muted">{item.warehouse_name}</div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
        {items.length === 0 && <div className="empty">{busy ? "加载中…" : "这段时间没有订单。"}</div>}
        {total > 0 && <Pager page={page} pageSize={pageSize} total={total} onChange={(next) => load(tab, next)} />}
      </div>

      {detail && (
        <div className="modal-backdrop" onClick={() => setDetail(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>{detail.posting_number}</h2>
            <p className="muted">{detail.order_number} · {detail.status}</p>
            {detail.products.map((product) => (
              <div key={`${product.offer_id}-${product.sku}`}>
                {product.name} × {product.quantity} · {product.price}
              </div>
            ))}
            {detail.cancel_reason && (
              <p>
                取消原因：{detail.cancel_reason}
                {detail.cancellation_initiator ? `（${detail.cancellation_initiator}）` : ""}
              </p>
            )}
            <button className="ghost" onClick={() => setDetail(null)}>关闭</button>
          </div>
        </div>
      )}
    </section>
  );
}
