import "@testing-library/jest-dom";
import { vi } from "vitest";

// jsdom does not implement scrollIntoView — cmdk calls it on selected items
Element.prototype.scrollIntoView = vi.fn();

// jsdom does not implement ResizeObserver — cmdk uses it internally
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};

// jsdom does not implement window.matchMedia — stub it globally
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});
