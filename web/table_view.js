// One table element built from table.columns and table.rows only.

export class TableView {
  render(table) {
    const node = document.createElement("table");
    node.appendChild(this._head(table.columns));
    node.appendChild(this._body(table));
    return node;
  }

  _head(columns) {
    const head = document.createElement("thead");
    const row = document.createElement("tr");
    for (const column of columns) {
      const cell = document.createElement("th");
      cell.textContent = column;
      row.appendChild(cell);
    }
    head.appendChild(row);
    return head;
  }

  _body(table) {
    const body = document.createElement("tbody");
    table.rows.forEach((record, index) => {
      body.appendChild(this._row(table.columns, record, index));
    });
    return body;
  }

  _row(columns, record, index) {
    const tr = document.createElement("tr");
    tr.dataset.index = String(index);
    for (const column of columns) {
      const cell = document.createElement("td");
      cell.textContent = TableView.cellText(record[column]);
      tr.appendChild(cell);
    }
    return tr;
  }

  static cellText(value) {
    if (value === null || value === undefined) return "";
    if (Array.isArray(value)) return value.map(TableView.cellText).join(", ");
    if (typeof value === "object") return JSON.stringify(value);
    return String(value);
  }
}
