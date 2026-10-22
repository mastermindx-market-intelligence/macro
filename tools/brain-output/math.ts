import katex from "katex";
// Only explicit math nodes made by the existing Markdown renderer are eligible.
// Native MathML avoids another font/CSS dependency on both application hosts.
export function render(root: HTMLElement): void {
  const nodes = Array.from(root.querySelectorAll<HTMLElement>("[data-mmb-math]")).slice(0, 32);
  for (const node of nodes) {
    if (node.dataset.mmbMathRendered) continue;
    const formula = node.textContent || "";
    if (!formula || formula.length > 4000) continue;
    try {
      katex.render(formula, node, {
        output: "mathml", displayMode: node.dataset.mmbMath === "display",
        trust: false, throwOnError: true, strict: "error",
        maxSize: 12, maxExpand: 200, macros: {},
      });
      node.dataset.mmbMathRendered = "true";
    } catch (_) {
      // Preserve readable source when unsupported, oversized or malformed.
      node.textContent = formula;
      node.classList.add("mmb-math-fallback");
    }
  }
}
