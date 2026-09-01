import { FormEvent, useEffect, useState } from "react";
import { api, Settings } from "../api";

export default function SettingsPage() {
  const [data, setData] = useState<Settings | null>(null);
  const [clientId, setClientId] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    const settings = await api.settings();
    setData(settings);
    setClientId(settings.client_id);
  }

  useEffect(() => {
    load().catch((err: Error) => setError(err.message));
  }, []);

  async function onSave(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const saved = await api.saveSettings({ client_id: clientId, api_key: apiKey || undefined });
      setData(saved);
      setApiKey("");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function onTest() {
    setBusy(true);
    setError("");
    try {
      setData(await api.testSettings());
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
          <h1>设置</h1>
          <p>Ozon 需要 Client-Id 和 Api-Key。密钥只保存在本机 SQLite / .env，不会发给前端明文。</p>
        </div>
      </div>
      <div className="panel" style={{ padding: 22, maxWidth: 560 }}>
        <form className="form-grid" onSubmit={onSave}>
          <label>
            Client-Id
            <input value={clientId} onChange={(e) => setClientId(e.target.value)} placeholder="卖家后台里的数字 ID" />
          </label>
          <label>
            Api-Key {data?.api_key_masked ? `（当前 ${data.api_key_masked}）` : ""}
            <input
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="留空则保留已保存的密钥"
            />
          </label>
          {error && <div className="error">{error}</div>}
          {data?.message && <div className={data.connected ? "ok" : "error"}>{data.message}</div>}
          {data?.company_name && <div className="ok">店铺：{data.company_name}</div>}
          <div className="actions">
            <button className="btn" disabled={busy}>保存</button>
            <button className="ghost" type="button" disabled={busy} onClick={onTest}>测试连接</button>
          </div>
        </form>
      </div>
    </section>
  );
}
