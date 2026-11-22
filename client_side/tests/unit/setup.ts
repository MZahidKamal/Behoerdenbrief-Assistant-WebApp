/**
 * Shared setup for all unit and component tests.
 * Removes rendered components after each test, so tests stay independent.
 */
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(() => {
  cleanup();
});
