// Where the collapsed message button rests: right of the "chat" menu pill in chat view, else below the MODS rail.
const RAIL_INSET = 14;
const GAP_BELOW_RAIL = 16;
const GAP_RIGHT_OF_PILL = 16;

export class DockCollapsedAnchor {
  corner(dock, root) {
    const pill = root.querySelector(".chat-head") && root.querySelector('.top-nav [aria-current="page"]');
    if (pill) return this._besidePill(dock, pill);
    const rail = root.querySelector(".rail");
    if (!rail) return null;
    const box = rail.getBoundingClientRect();
    return { left: box.left + RAIL_INSET, top: box.bottom + GAP_BELOW_RAIL };
  }

  _besidePill(dock, pill) {
    const box = pill.getBoundingClientRect();
    return { left: box.right + GAP_RIGHT_OF_PILL, top: box.top + (box.height - dock.offsetHeight) / 2 };
  }

  apply(dock, root) {
    const corner = this.corner(dock, root);
    if (!corner) return this.clear(dock);
    dock.style.left = `${corner.left}px`;
    dock.style.top = `${corner.top}px`;
    dock.style.right = "auto";
    dock.style.bottom = "auto";
  }

  clear(dock) {
    dock.style.left = dock.style.top = dock.style.right = dock.style.bottom = "";
  }
}
