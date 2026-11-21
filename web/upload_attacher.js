// Attaching files to a chat: upload each file, then add its server path to the input.

export class UploadAttacher {
  constructor(chatStream, onError) {
    this._chatStream = chatStream;
    this._onError = onError;
  }

  async attach(name, files, input) {
    const paths = [];
    for (const file of files) {
      try {
        paths.push(await this._chatStream.upload(name, file));
      } catch (error) {
        this._onError(String(error));
      }
    }
    if (paths.length > 0) {
      let value = input.value;
      if (value !== "" && !value.endsWith("\n")) value += "\n";
      input.value = value + paths.join("\n");
    }
    input.dispatchEvent(new Event("input"));
    input.focus();
  }

  bindDrop(element, nameProvider, input) {
    element.addEventListener("dragover", (event) => {
      event.preventDefault();
      element.classList.add("is-dropping");
    });
    element.addEventListener("dragleave", () => {
      element.classList.remove("is-dropping");
    });
    element.addEventListener("drop", (event) => {
      event.preventDefault();
      element.classList.remove("is-dropping");
      const name = nameProvider();
      if (name !== null) this.attach(name, event.dataTransfer.files, input);
    });
  }

  bindPaste(input, nameProvider) {
    input.addEventListener("paste", (event) => {
      const images = Array.from(event.clipboardData.files).filter((file) => file.type.startsWith("image/"));
      if (images.length === 0) return;
      event.preventDefault();
      const renamedFiles = images.map((file, index) => {
        const extension = file.type.slice("image/".length) || "png";
        return new File([file], `pasted-${Date.now()}-${index}.${extension}`, { type: file.type });
      });
      const name = nameProvider();
      if (name !== null) this.attach(name, renamedFiles, input);
    });
  }
}
