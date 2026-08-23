document.addEventListener("alpine:init", () => {
  Alpine.data("employeeDirectory", (initialEmployees) => ({
    employees: initialEmployees,
    query: "",
    loading: true,
    formError: "",
    showModal: false,
    get filtered() {
      const q = this.query.trim().toLowerCase();
      if (!q) return this.employees;
      return this.employees.filter(
        (e) =>
          e.name.toLowerCase().includes(q) ||
          e.designation.toLowerCase().includes(q) ||
          e.department.toLowerCase().includes(q)
      );
    },
    init() {
      setTimeout(() => {
        this.loading = false;
        this.$nextTick(() => staggerRows(this.$refs.tbody));
      }, 400);
    },
  }));

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
