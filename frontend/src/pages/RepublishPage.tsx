import { useEffect, useState } from "react";
import { api, Product, RepublishJob } from "../api";

export default function RepublishPage() {
  const [items, setItems] = useState<Product[]>([]);
  const [jobs, setJobs] = useState<RepublishJob[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    const [products, jobRows] = await Promise.all([
      api.products({ visibility: "REMOVED" }),
      api.jobs(),
    ]);
    const archived = await api.products({ visibility: "ARCHIVED" });
    const map = new Map<number, Product>();
    [...products, ...archived].forEach((item) => map.set(item.product_id, item));
    setItems([...map.values()]);
    setJobs(jobRows);
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
          <h1>复刊中心</h1>
          <p>已下架或归档的商品。复制会生成新卡片：先按 SKU，失败再用本地快照。归档恢复请到商品页点「恢复」。</p>
        </div>
        <button className="ghost" disabled={busy} onClick={() => run(load)}>刷新</button>
      </div>
      {error && <div className="error">{error}</div>}
      <div className="panel" style={{ marginBottom: 22 }}>
        <table>
          <thead>
            <tr>
              <th>商品</th>
              <th>状态</th>
              <th>快照</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.product_id} className={item.is_removed ? "removed" : undefined}>
                <td>
                  <div>{item.name || item.offer_id}</div>
                  <div className="muted">{item.offer_id}</div>
                </td>
                <td>
                  <span className={`badge ${item.is_removed ? "red" : item.is_archived ? "archived" : ""}`}>
                    {item.status_label}
                  </span>
                </td>
                <td>{item.has_snapshot ? "已缓存" : "缺失，请先同步"}</td>
                <td>
                  <button className="btn" disabled={busy} onClick={() => run(() => api.copyProduct(item.product_id, {}))}>
                    复制
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {items.length === 0 && <div className="empty">当前没有下架或归档商品。</div>}
      </div>
      <h2>复刊 / 导入任务</h2>
      <div className="panel">
        <table>
          <thead>
            <tr>
              <th>时间</th>
              <th>策略</th>
              <th>新货号</th>
              <th>状态</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {jobs.map((job) => (
              <tr key={job.id}>
                <td>{new Date(job.created_at).toLocaleString()}</td>
                <td>{job.strategy}</td>
                <td>{job.new_offer_id}</td>
                <td>
                  <div>{job.status}</div>
                  <div className="muted">{job.message.slice(0, 160)}</div>
                </td>
                <td>
                  {job.task_id && (
                    <button className="ghost" disabled={busy} onClick={() => run(() => api.refreshJob(job.id))}>
                      刷新进度
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
