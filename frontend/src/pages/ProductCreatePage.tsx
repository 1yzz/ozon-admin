import { FormEvent, useEffect, useMemo, useState } from "react";
import { api, CategoryAttribute, CategoryNode } from "../api";

type Leaf = {
  label: string;
  description_category_id: number;
  type_id: number;
};

type UploadedImage = {
  filename: string;
  url: string;
  original_name: string;
};

function flatten(nodes: CategoryNode[], prefix: string[] = []): Leaf[] {
  const leaves: Leaf[] = [];
  for (const node of nodes) {
    const name = node.type_name || node.category_name || "";
    const path = name ? [...prefix, name] : prefix;
    if (node.type_id && node.description_category_id && !node.disabled) {
      leaves.push({
        label: path.join(" / "),
        description_category_id: node.description_category_id,
        type_id: node.type_id,
      });
    }
    if (node.children?.length) {
      leaves.push(...flatten(node.children, path));
    }
  }
  return leaves;
}

export default function ProductCreatePage() {
  const [tree, setTree] = useState<CategoryNode[]>([]);
  const [leafKey, setLeafKey] = useState("");
  const [attrs, setAttrs] = useState<CategoryAttribute[]>([]);
  const [attrValues, setAttrValues] = useState<Record<number, string>>({});
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [images, setImages] = useState<UploadedImage[]>([]);
  const [form, setForm] = useState({
    name: "",
    description: "",
    offer_id: "",
    price: "",
    old_price: "",
    vat: "0.20",
    depth: "100",
    width: "100",
    height: "100",
    weight: "100",
  });
  const [ru, setRu] = useState({ name_ru: "", description_ru: "" });

  useEffect(() => {
    api.categories().then(setTree).catch((err: Error) => setError(err.message));
  }, []);

  const leaves = useMemo(() => flatten(tree).slice(0, 4000), [tree]);
  const selected = leaves.find((leaf) => `${leaf.description_category_id}:${leaf.type_id}` === leafKey);

  useEffect(() => {
    if (!selected) return;
    api.attributes(selected.description_category_id, selected.type_id)
      .then(setAttrs)
      .catch((err: Error) => setError(err.message));
  }, [leafKey]);

  async function onUpload(fileList: FileList | null) {
    if (!fileList?.length) return;
    setBusy(true);
    setError("");
    try {
      const result = await api.uploadImages(Array.from(fileList));
      setImages((current) => [...current, ...result.items]);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function onTranslate() {
    if (!form.name.trim() && !form.description.trim()) {
      setError("请先填写中文名称或描述");
      return;
    }
    setBusy(true);
    setError("");
    try {
      setRu(await api.translateListing({ name: form.name, description: form.description }));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!selected) {
      setError("请选择类目");
      return;
    }
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const attributes = attrs
        .filter((attr) => attrValues[attr.id]?.trim())
        .map((attr) => ({
          id: attr.id,
          complex_id: 0,
          values: [{ value: attrValues[attr.id] }],
        }));
      const result = await api.createProduct({
        ...form,
        description_category_id: selected.description_category_id,
        type_id: selected.type_id,
        depth: Number(form.depth),
        width: Number(form.width),
        height: Number(form.height),
        weight: Number(form.weight),
        images: images.map((item) => item.url),
        attributes,
      });
      setRu({ name_ru: result.name_ru, description_ru: result.description_ru });
      setMessage(`已提交创建任务，task_id=${result.task_id}。提交给 Ozon 的俄文标题：${result.name_ru}`);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const required = attrs.filter((attr) => attr.is_required);

  return (
    <section>
      <div className="page-head">
        <div>
          <h1>新上架</h1>
          <p>名称和描述填中文，翻译走本地 Redis 队列后再提交给 Ozon。图片上传到 data/uploads/products/。</p>
        </div>
      </div>
      <form className="panel" style={{ padding: 22 }} onSubmit={onSubmit}>
        <div className="form-grid">
          <label>
            类目
            <select value={leafKey} onChange={(e) => setLeafKey(e.target.value)}>
              <option value="">选择类目 / 类型</option>
              {leaves.map((leaf) => (
                <option key={`${leaf.description_category_id}:${leaf.type_id}`} value={`${leaf.description_category_id}:${leaf.type_id}`}>
                  {leaf.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            名称（中文）
            <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required placeholder="例如：儿童益智积木套装" />
          </label>
          {ru.name_ru && <div className="muted">俄文标题：{ru.name_ru}</div>}
          <label>
            商品描述（中文）
            <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="材质、尺寸、适用年龄、包装内容等" />
          </label>
          {ru.description_ru && <div className="muted">俄文描述：{ru.description_ru}</div>}
          <div>
            <button className="ghost" type="button" disabled={busy} onClick={onTranslate}>预览俄文翻译</button>
          </div>
          <label>货号 offer_id<input value={form.offer_id} onChange={(e) => setForm({ ...form, offer_id: e.target.value })} required /></label>
          <label>价格<input value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} required /></label>
          <label>划线价<input value={form.old_price} onChange={(e) => setForm({ ...form, old_price: e.target.value })} /></label>
          <label>
            VAT
            <select value={form.vat} onChange={(e) => setForm({ ...form, vat: e.target.value })}>
              <option value="0">0</option>
              <option value="0.05">5%</option>
              <option value="0.10">10%</option>
              <option value="0.20">20%</option>
            </select>
          </label>
          <label>长 / 宽 / 高 (mm)
            <div className="toolbar">
              <input value={form.depth} onChange={(e) => setForm({ ...form, depth: e.target.value })} />
              <input value={form.width} onChange={(e) => setForm({ ...form, width: e.target.value })} />
              <input value={form.height} onChange={(e) => setForm({ ...form, height: e.target.value })} />
            </div>
          </label>
          <label>重量 (g)<input value={form.weight} onChange={(e) => setForm({ ...form, weight: e.target.value })} /></label>
          <label>
            商品图片
            <input type="file" accept="image/jpeg,image/png,image/webp" multiple onChange={(e) => onUpload(e.target.files)} />
          </label>
          {images.length > 0 && (
            <div className="upload-grid">
              {images.map((item) => (
                <figure key={item.filename}>
                  <img src={item.url.replace("http://127.0.0.1:8000", "")} alt={item.original_name} />
                  <button type="button" className="ghost" onClick={() => setImages((current) => current.filter((row) => row.filename !== item.filename))}>
                    移除
                  </button>
                </figure>
              ))}
            </div>
          )}
          {required.map((attr) => (
            <label key={attr.id}>
              {attr.name}{attr.is_required ? " *" : ""}
              <input
                value={attrValues[attr.id] || ""}
                onChange={(e) => setAttrValues({ ...attrValues, [attr.id]: e.target.value })}
                placeholder={attr.description}
              />
            </label>
          ))}
        </div>
        {error && <div className="error">{error}</div>}
        {message && <div className="ok">{message}</div>}
        <div className="actions" style={{ marginTop: 16 }}>
          <button className="btn" disabled={busy}>提交上架</button>
        </div>
      </form>
    </section>
  );
}
