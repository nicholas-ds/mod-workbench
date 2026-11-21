// Keyboard to action for one question: 1, 2, 3 pick an option, Enter takes the default, S skips.

export class KeyMap {
  static actionFor(key, question) {
    if (key === "Enter" && KeyMap._hasDefault(question)) return { type: "default" };
    if (key === "s" || key === "S") return { type: "skip" };
    const option = KeyMap._optionAt(question, key);
    return option ? { type: "pick", id: option.id } : null;
  }

  static _hasDefault(question) {
    return Boolean(question.default)
      || (question.type === "yes" && Boolean(question.suggestion));
  }

  static _optionAt(question, key) {
    const slot = ["1", "2", "3"].indexOf(key);
    if (slot === -1) return null;
    return question.options[slot] || null;
  }
}
