/**
 * Component tests for the start page placeholder.
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import HomePage from "@/app/page";

describe("HomePage", () => {
  it("test_render_home_page_shows_main_element_when_page_opens", () => {
    render(<HomePage />);

    const mainElement = screen.getByRole("main");

    expect(mainElement).toBeDefined();
  });
});
