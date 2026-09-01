import { useEffect, useState } from "react";
import { api, Dashboard } from "../api";

export default function DashboardPage() {
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.dashboard().then(setData).catch((err: Error) => setError(err.message));
  }, []);

  return (
    <section>
      <div className="page-head">
        <div>
          <h1>工作台</h1>
          <p>先同步商品和仓库，再处理复刊、改价和改库存。</p>
        </div>
      </div>
      {error && <div className="error">{error}</div>}
      <div className="cards">
        <div className="card"><span>商品总数</span><b>{data?.product_total ?? "-"}</b></div>
        <div className="card"><span>在售</span><b>{data?.in_sale ?? "-"}</b></div>
        <div className="card"><span>被下架 / 隐藏</span><b>{data?.removed ?? "-"}</b></div>
        <div className="card"><span>已归档</span><b>{data?.archived ?? "-"}</b></div>
        <div className="card"><span>红色指数</span><b>{data?.red_price ?? "-"}</b></div>
        <div className="card"><span>黄色指数</span><b>{data?.yellow_price ?? "-"}</b></div>
        <div className="card"><span>零库存</span><b>{data?.empty_stock ?? "-"}</b></div>
        <div className="card"><span>FBS 仓库</span><b>{data?.warehouse_count ?? "-"}</b></div>
      </div>
      <p className="muted">最近同步：{data?.last_sync ? new Date(data.last_sync).toLocaleString() : "尚未同步"}</p>
    </section>
  );
}
