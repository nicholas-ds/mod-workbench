// Creation of DOM nodes. Every view builds its nodes through this class.

export class DomBuilder {
  static el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }
}
