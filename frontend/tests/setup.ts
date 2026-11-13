import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

class RO { observe() {} unobserve() {} disconnect() {} }
(globalThis as unknown as { ResizeObserver: typeof RO }).ResizeObserver = RO;
afterEach(() => cleanup());
