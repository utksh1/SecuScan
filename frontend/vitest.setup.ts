import '@testing-library/jest-dom';

function createStorageMock() {
  const store = new Map<string, string>();
  const handler = {
    getItem: (key: string) => (store.has(key) ? store.get(key)! : null),
    setItem: (key: string, value: string) => {
      store.set(key, String(value));
    },
    removeItem: (key: string) => {
      store.delete(key);
    },
    clear: () => {
      store.clear();
    },
    key: (index: number) => Array.from(store.keys())[index] ?? null,
    get length() {
      return store.size;
    },
  };

  return new Proxy(handler, {
    get(target, prop) {
      if (prop === 'length') {
        return store.size;
      }
      if (typeof prop === 'string' && !isNaN(Number(prop))) {
        return Array.from(store.entries())[Number(prop)]?.[1] ?? null;
      }
      if (prop in target) {
        return (target as any)[prop];
      }
      return store.get(String(prop)) ?? null;
    },
    ownKeys() {
      return Array.from(store.keys());
    },
    getOwnPropertyDescriptor(target, prop) {
      if (store.has(String(prop))) {
        return {
          configurable: true,
          enumerable: true,
          value: store.get(String(prop)),
        };
      }
      if (prop in target) {
        return Object.getOwnPropertyDescriptor(target, prop);
      }
      return undefined;
    },
  });
}

if (!window.localStorage || typeof window.localStorage.getItem !== 'function') {
  const storage = createStorageMock();
  Object.defineProperty(window, 'localStorage', {
    value: storage,
    configurable: true,
  });
  Object.defineProperty(globalThis, 'localStorage', {
    value: storage,
    configurable: true,
  });
}
