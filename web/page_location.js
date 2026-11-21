// Mirrors the view context into the URL hash so a refresh restores the page location.

import { LocationHash } from "./location_hash.js";

const CONTEXT_EVENT = "wb-context";

export class PageLocation {
  start() {
    document.addEventListener(CONTEXT_EVENT, (event) => this._save(event.detail));
  }

  read() {
    return LocationHash.parse(window.location.hash);
  }

  _save(context) {
    const hash = LocationHash.format(context);
    if (hash) history.replaceState(null, "", hash);
  }
}
