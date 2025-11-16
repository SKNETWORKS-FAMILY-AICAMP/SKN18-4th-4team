(function () {
  document.addEventListener("DOMContentLoaded", () => {
    const graphModal = document.getElementById("graphModal");
    const graphModalBody = document.getElementById("graphModalBody");
    const closeBtn = document.getElementById("graphModalCloseBtn");
    const backdrop = graphModal?.querySelector(".graph-modal__backdrop");

    if (!graphModal || !graphModalBody) return;

    function showLoading() {
      graphModal.classList.remove("hidden");
      graphModalBody.innerHTML = `
        <div class="graph-modal__loading">
          <div class="graph-modal__spinner"></div>
          <p>그래프를 생성하는 중입니다...</p>
        </div>
      `;
    }

    function normalizeGraphCode(raw = "") {
      const trimmed = (raw || "").trim();
      if (!trimmed) return "";
      if (trimmed.startsWith("```")) {
        const cleaned = trimmed.replace(/^```[a-zA-Z]*\s*/, "").replace(/```$/, "");
        return wrapNodeLabels(cleaned.trim());
      }
      return wrapNodeLabels(trimmed);
    }

    function wrapNodeLabels(code) {
      return code.replace(/\[([^\]]+)\]/g, (match, content) => {
        const text = content.trim();
        if (
          (text.startsWith('"') && text.endsWith('"')) ||
          (text.startsWith("'") && text.endsWith("'"))
        ) {
          return `[${text}]`;
        }
        const escaped = text.replace(/"/g, '\\"');
        return `["${escaped}"]`;
      });
    }

    async function renderGraph(code = "") {
      const graphCode = normalizeGraphCode(code);

      if (!graphCode) {
        graphModalBody.innerHTML = `<p class="graph-modal__empty">그래프 데이터를 생성하지 못했습니다.</p>`;
        return;
      }

      try {
        const { svg } = await window.mermaid.render(`graph-${Date.now()}`, graphCode);
        graphModalBody.innerHTML = svg;
        const svgEl = graphModalBody.querySelector("svg");
        if (svgEl) {
          svgEl.setAttribute("width", "100%");
          svgEl.setAttribute("height", "100%");
          svgEl.style.maxWidth = "100%";
        }
      } catch (err) {
        console.error("Mermaid render error:", err);
        graphModalBody.innerHTML = `<pre class="graph-modal__error">${graphCode}</pre>`;
      }
    }

    window.chatGraph = {
      open(graphCode = "") {
        showLoading();
        requestAnimationFrame(() => renderGraph(graphCode));
      },
      close() {
        graphModal.classList.add("hidden");
        graphModalBody.innerHTML = "";
      },
      showLoading,
    };

    function closeModal() {
      window.chatGraph.close();
    }

    if (closeBtn) closeBtn.addEventListener("click", closeModal);
    if (backdrop) backdrop.addEventListener("click", closeModal);
  });
})();
