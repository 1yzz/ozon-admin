import { useEffect, useState } from "react";
import { api, Warehouse } from "../api";

export default function WarehousesPage() {
  const [items, setItems] = useState<Warehouse[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    setItems(await api.warehouses());
  }

  useEffect(() => {
    load().catch((err: Error) => setError(err.message));
  }, []);

  return (
    <section>
      <div className="page-head">
        <div>
          <h1>仓库</h1>
          <p>只读查看 FBS / rFBS 仓库。改库存请到商品页。</p>
        </div>
        <button
          className="btn"
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            setError("");
            try {
              await api.syncWarehouses();
              await load();
            } catch (err) {
              setError((err as Error).message);
            } finally {
              setBusy(false);
            }
          }}
        >
          同步仓库
        </button>
      </div>
      {error && <div className="error">{error}</div>}
      <div className="panel">
        <table>
          <thead>
            <tr>
              <th>仓库</th>
              <th>类型</th>
              <th>状态</th>
              <th>地址</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.warehouse_id}>
                <td>
                  <div>{item.name}</div>
                  <div className="muted">ID {item.warehouse_id}</div>
                </td>
                <td>{item.warehouse_type || (item.is_rfbs ? "rFBS" : "FBS")}</td>
                <td>{item.status}</td>
                <td>{item.address || "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {items.length === 0 && <div className="empty">还没有仓库数据，点右上角同步。</div>}
      </div>
    </section>
  );
}
