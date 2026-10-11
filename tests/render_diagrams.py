"""
Mermaid Diagram Renderer using Playwright.
Renders all .mmd diagrams in docs/diagrams/ to high-resolution PNG images.
"""

import os
import glob
from playwright.sync_api import sync_playwright

DIAGRAMS_DIR = os.path.join(os.path.dirname(__file__), "..", "docs", "diagrams")

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
  <style>
    body {{
      margin: 20px;
      background: white;
      font-family: 'Helvetica Neue', Arial, sans-serif;
    }}
    .mermaid {{
      display: inline-block;
    }}
  </style>
</head>
<body>
  <div class="mermaid">
{mmd_content}
  </div>
  <script>
    mermaid.initialize({{
      startOnLoad: true,
      theme: 'default',
      securityLevel: 'loose',
      fontFamily: 'Helvetica Neue, Arial, sans-serif'
    }});
  </script>
</body>
</html>
"""


def render_all_diagrams():
    mmd_files = glob.glob(os.path.join(DIAGRAMS_DIR, "*.mmd"))
    print(f"Found {len(mmd_files)} Mermaid diagram files to render...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(device_scale_factor=2)

        for mmd_path in mmd_files:
            base_name = os.path.splitext(os.path.basename(mmd_path))[0]
            png_path = os.path.join(DIAGRAMS_DIR, f"{base_name}.png")

            with open(mmd_path, "r", encoding="utf-8") as f:
                mmd_content = f.read()

            html = HTML_TEMPLATE.format(mmd_content=mmd_content)
            page.set_content(html)
            try:
                page.wait_for_selector(".mermaid svg", timeout=6000)
                svg_el = page.query_selector(".mermaid svg")
                if svg_el:
                    svg_el.screenshot(path=png_path)
                    print(f"✓ Rendered: {base_name}.png")
                else:
                    page.screenshot(path=png_path)
                    print(f"✓ Rendered (full): {base_name}.png")
            except Exception as e:
                print(f"✗ Failed to render {base_name}: {e}")

        browser.close()
    print("All diagrams processed!")


if __name__ == "__main__":
    render_all_diagrams()
