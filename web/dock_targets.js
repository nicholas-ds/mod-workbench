// Labels for the dock target picker: SDK orchestrators first, then terminal panes.

const SDK_KIND = "sdk";
const PANE_KIND = "pane";
const PANE_PREFIX = "terminal: ";
const MAIN_LABEL = "main";
const TERMINAL_FRESH_MS = 30 * 60 * 1000;

export class DockTargets {
  constructor() {
    this._sdkNames = [];
    this._panes = [];
  }

  /** @param {string[]} names */
  setSdkNames(names) {
    this._sdkNames = names;
  }

  /**
   * @param {{name: string, mod: string, active_at: string}[]} panes
   */
  setPanes(panes) {
    this._panes = panes.filter((pane) => DockTargets.isActiveRecently(pane.active_at));
  }

  /**
   * @param {string} activeAt
   * @returns {boolean}
   */
  static isActiveRecently(activeAt) {
    const activeMs = Date.parse(activeAt);
    if (Number.isNaN(activeMs)) return false;
    return Date.now() - activeMs <= TERMINAL_FRESH_MS;
  }

  /** @returns {string[]} */
  labels() {
    return [...this._sdkNames, ...this._panes.map((pane) => `${PANE_PREFIX}${pane.name}`)];
  }

  /** @param {string} label @returns {{kind: string, name: string}|null} */
  resolve(label) {
    if (this._sdkNames.includes(label)) return { kind: SDK_KIND, name: label };
    const pane = this._panes.find((entry) => `${PANE_PREFIX}${entry.name}` === label);
    if (pane) return { kind: PANE_KIND, name: pane.name };
    return null;
  }

  /** @param {string} folder repo folder of an agent @returns {string|null} */
  paneLabelForFolder(folder) {
    const repo = folder.split(/[\/]/).filter(Boolean).pop();
    const pane = this._panes.find((entry) => entry.mod === repo);
    return pane ? `${PANE_PREFIX}${pane.name}` : null;
  }

  /** @returns {{name: string, mod: string, active_at: string}|null} */
  _latestPane() {
    let latest = null;
    for (const pane of this._panes) {
      if (!latest || Date.parse(pane.active_at) > Date.parse(latest.active_at)) {
        latest = pane;
      }
    }
    return latest;
  }

  /**
   * Most recently active terminal pane's label, else the old SDK fallback order.
   * @param {string} modName @returns {string}
   */
  defaultLabel(modName) {
    const pane = this._latestPane();
    if (pane) return `${PANE_PREFIX}${pane.name}`;
    if (this._sdkNames.includes(modName)) return modName;
    if (this._sdkNames.includes(MAIN_LABEL)) return MAIN_LABEL;
    return this.labels()[0] ?? "";
  }
}
