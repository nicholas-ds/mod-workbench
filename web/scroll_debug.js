// Debug overlay for scroll bars. Open the workbench with ?debug=scroll to see it.

import { DomBuilder } from "./dom_builder.js";

const REFRESH_MS = 1000;

export class ScrollDebugOverlay {
  static enabled() {
    return new URLSearchParams(location.search).get("debug") === "scroll";
  }

  start() {
    const link = DomBuilder.el("link");
    link.rel = "stylesheet";
    link.href = "scroll_debug.css";
    document.head.appendChild(link);
    document.body.classList.add("debug-scroll");
    this._panel = DomBuilder.el("pre", "scroll-debug-panel clay-small");
    document.body.appendChild(this._panel);
    this._refresh();
    setInterval(() => this._refresh(), REFRESH_MS);
  }

  _refresh() {
    const lines = [this._environmentLine(), ...this._scrollerLines()];
    this._panel.textContent = lines.join("\n");
  }

  _environmentLine() {
    const scale = window.visualViewport ? window.visualViewport.scale : 1;
    return `window ${innerWidth}x${innerHeight}  dpr ${devicePixelRatio}  pinch ${scale}  ${navigator.userAgent.match(/(Edg|Chrome)\/[\d.]+/)?.[0] ?? "browser?"}`;
  }

  _scrollerLines() {
    const tracks = [...document.querySelectorAll(".scroll-track:not([hidden])")];
    return tracks.map((track, index) => this._trackLine(track, index));
  }

  _trackLine(track, index) {
    const scroller = track.previousElementSibling;
    const card = track.closest(".clay").getBoundingClientRect();
    const bar = track.getBoundingClientRect();
    const rows = [
      `[${index}] content ${scroller.scrollWidth}px in ${scroller.clientWidth}px`,
      `    bar ${bar.width.toFixed(1)}x${bar.height.toFixed(1)}  to card bottom ${(card.bottom - bar.bottom).toFixed(1)}px`,
      `    to card left ${(bar.left - card.left).toFixed(1)}px  to card right ${(card.right - bar.right).toFixed(1)}px`,
    ];
    return rows.join("\n");
  }
}
