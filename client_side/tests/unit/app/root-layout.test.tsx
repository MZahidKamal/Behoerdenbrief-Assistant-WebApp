/**
 * Component tests for the root layout.
 * The layout returns the <html> element, which cannot be rendered inside a
 * test container, so it is rendered to an HTML string instead.
 */
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import RootLayout from "@/app/layout";

describe("RootLayout", () => {
  it("test_render_root_layout_wraps_children_in_body_when_rendered", () => {
    const childContent = <p>Child content</p>;

    const htmlMarkup = renderToStaticMarkup(
      <RootLayout params={Promise.resolve({})}>{childContent}</RootLayout>,
    );

    expect(htmlMarkup).toContain('<html lang="en"');
    expect(htmlMarkup).toMatch(/<body[^>]*><p>Child content<\/p><\/body>/);
  });
});
