import { useEffect, useState } from "react";
import Pager from "../Pager";
import { api, ReturnItem } from "../api";

type Group = "all" | "in_transit" | "utilization";

function formatDate(value: string): string {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return `${date.getDate()} ${date.getMonth() + 1}月`;
}

function isUtilization(item: ReturnItem): boolean {
  const blob = `${item.status} ${item.status_sys}`.toLowerCase();
  return ["核销", "销毁", "utiliz"].some((key) => blob.includes(key));
}

export default function ReturnsPage() {
  const [group, setGroup] = useState<Group>("all");
  const [items, setItems] = useState<ReturnItem[]>([]);
  const [days, setDays] = useState(30);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const pageSize = 20;
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [detail, setDetail] = useState<ReturnItem | null>(null);

  async function load(nextGroup = group, nextPage = page, nextDays = days) {
    setBusy(true);
    setError("");
    try {
      const result = await api.returns({
        days: nextDays,
        group: nextGroup,
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

  return (
    <section>
      <div className="page-head">
        <div>
          <h1>退货和取消</h1>
          <p>只读查看 FBS 退货与取消申请，数据来自 Ozon /v1/returns/list。</p>
        </div>
        <div className="toolbar">
          <select value={days} onChange={(e) => { const next = Number(e.target.value); setDays(next); load(group, 1, next); }}>
            <option value={14}>近 14 天</option>
            <option value={30}>近 30 天</option>
            <option value={90}>近 90 天</option>
          </select>
          <button className="ghost" disabled={busy} onClick={() => load(group, 1)}>刷新</button>
        </div>
      </div>
      <div className="tabs">
        <button className="ghost" aria-current={group === "in_transit"} onClick={() => { setGroup("in_transit"); load("in_transit", 1); }}>在途中的</button>
        <button className="ghost" aria-current={group === "utilization"} onClick={() => { setGroup("utilization"); load("utilization", 1); }}>销毁和核销</button>
        <button className="ghost" aria-current={group === "all"} onClick={() => { setGroup("all"); load("all", 1); }}>全部</button>
      </div>
      {error && <div className="error">{error}</div>}
      <div className="panel">
        <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>模式</th>
              <th>状态日期</th>
              <th>申请 / 类型</th>
              <th>状态</th>
              <th>货件编号</th>
              <th>商品</th>
              <th>价格</th>
              <th>目的地址</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id} onClick={() => setDetail(item)} style={{ cursor: "pointer" }}>
                <td>{item.mode || "FBS"}</td>
                <td>{formatDate(item.status_at || item.return_date)}</td>
                <td>
                  <div>{item.id}</div>
                  <div className="muted">{item.type_label || item.type || "-"}</div>
                </td>
                <td>
                  <span className={`badge ${isUtilization(item) ? "warn" : "sale"}`}>
                    {item.status || "-"}
                  </span>
                </td>
                <td>{item.posting_number || "-"}</td>
                <td>
                  <div>{item.product_name || item.offer_id || "-"}</div>
                  <div className="muted">{item.offer_id}{item.sku ? ` · SKU ${item.sku}` : ""} × {item.quantity}</div>
                </td>
                <td>{item.price ? `${item.price} ${item.currency_code}` : "-"}</td>
                <td>{item.target_place || item.place_name || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
        {items.length === 0 && <div className="empty">{busy ? "加载中…" : "这段时间没有退货或取消。"}</div>}
        {total > 0 && <Pager page={page} pageSize={pageSize} total={total} onChange={(next) => load(group, next)} />}
      </div>

      {detail && (
        <div className="modal-backdrop" onClick={() => setDetail(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>{detail.type_label || "申请"} #{detail.id}</h2>
            <p className="muted">{detail.posting_number} · {detail.status}</p>
            <p>{detail.product_name}</p>
            {detail.reason && <p>原因：{detail.reason}</p>}
            <button className="ghost" onClick={() => setDetail(null)}>关闭</button>
          </div>
        </div>
      )}
    </section>
  );
}
