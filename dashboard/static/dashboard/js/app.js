document.addEventListener("alpine:init", () => {
  Alpine.data("toast", () => ({
    items: [],
    add(message) {
      const id = Date.now();
      this.items.push({ id, message });
      this.$nextTick(() => {
        const el = this.$root.querySelector(`[data-toast-id="${id}"]`);
        animateToastIn(el);
      });
      setTimeout(() => this.remove(id), 3500);
    },
    remove(id) {
      this.items = this.items.filter((t) => t.id !== id);
    },
  }));
});
