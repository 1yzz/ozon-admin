export type ToastKind = "error" | "ok";

export type ToastItem = {
  id: number;
  kind: ToastKind;
  text: string;
};

type Listener = (items: ToastItem[]) => void;

let nextId = 1;
const items: ToastItem[] = [];
const listeners = new Set<Listener>();

function emit() {
  const snapshot = [...items];
  listeners.forEach((listener) => listener(snapshot));
}

export function showToast(kind: ToastKind, text: string) {
  const message = (text || "").trim();
  if (!message) return;
  const item = { id: nextId++, kind, text: message };
  items.push(item);
  emit();
  window.setTimeout(() => {
    const index = items.findIndex((row) => row.id === item.id);
    if (index >= 0) {
      items.splice(index, 1);
      emit();
    }
  }, kind === "error" ? 8000 : 4000);
}

export function dismissToast(id: number) {
  const index = items.findIndex((row) => row.id === id);
  if (index >= 0) {
    items.splice(index, 1);
    emit();
  }
}

export function subscribeToasts(listener: Listener) {
  listeners.add(listener);
  listener([...items]);
  return () => {
    listeners.delete(listener);
  };
}
