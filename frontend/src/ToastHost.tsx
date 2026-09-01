import { useEffect, useState } from "react";
import { dismissToast, subscribeToasts, ToastItem } from "./toast";

export default function ToastHost() {
  const [items, setItems] = useState<ToastItem[]>([]);

  useEffect(() => subscribeToasts(setItems), []);

  if (!items.length) return null;

  return (
    <div className="toast-stack" aria-live="polite">
      {items.map((item) => (
        <button
          key={item.id}
          type="button"
          className={`toast ${item.kind}`}
          onClick={() => dismissToast(item.id)}
        >
          {item.text}
        </button>
      ))}
    </div>
  );
}
