// Extends Vitest's `expect` with @testing-library/jest-dom matchers (toBeInTheDocument, etc.)
import '@testing-library/jest-dom/vitest'

// Node 22 ships an experimental global `localStorage` (a partial stub missing
// `.clear`) that shadows jsdom's. Replace it with a complete in-memory store so
// the app's token/SEC-email helpers behave as in a browser.
class MemoryStorage implements Storage {
  private store = new Map<string, string>()
  get length(): number {
    return this.store.size
  }
  clear(): void {
    this.store.clear()
  }
  getItem(key: string): string | null {
    return this.store.has(key) ? (this.store.get(key) as string) : null
  }
  setItem(key: string, value: string): void {
    this.store.set(key, String(value))
  }
  removeItem(key: string): void {
    this.store.delete(key)
  }
  key(index: number): string | null {
    return Array.from(this.store.keys())[index] ?? null
  }
}

Object.defineProperty(globalThis, 'localStorage', {
  value: new MemoryStorage(),
  configurable: true,
  writable: true,
})

// jsdom has no ResizeObserver; recharts' ResponsiveContainer needs it.
class ResizeObserverMock {
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
}
if (!globalThis.ResizeObserver) {
  globalThis.ResizeObserver = ResizeObserverMock as unknown as typeof ResizeObserver
}
