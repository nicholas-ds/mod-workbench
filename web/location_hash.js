// The page location as a URL hash: an open board or a home section.

const SECTIONS = ["mods", "tasks", "chat"];

export class LocationHash {
  static format(context) {
    if (!context) return "";
    if (context.view === "board" && context.mod && context.board) {
      return "#/board/" + encodeURIComponent(context.mod) + "/" + encodeURIComponent(context.board);
    }
    if (context.view === "home" && SECTIONS.includes(context.section)) {
      return "#/section/" + encodeURIComponent(context.section);
    }
    return "";
  }

  static parse(hash) {
    if (typeof hash !== "string" || !hash.startsWith("#/")) return null;
    const parts = hash.slice(2).split("/").map((part) => decodeURIComponent(part));
    if (parts.length === 3 && parts[0] === "board" && parts[1] && parts[2]) {
      return { kind: "board", mod: parts[1], id: parts[2] };
    }
    if (parts.length === 2 && parts[0] === "section" && SECTIONS.includes(parts[1])) {
      return { kind: "section", section: parts[1] };
    }
    return null;
  }
}
