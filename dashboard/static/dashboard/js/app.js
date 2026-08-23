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
    openModal() {
      this.formError = "";
      this.showModal = true;
      this.$nextTick(() => animateModalIn(this.$refs.modalPanel));
    },
    closeModal() {
      animateModalOut(this.$refs.modalPanel, () => {
        this.showModal = false;
      });
    },
    addEmployee(form) {
      if (!form.name || !form.designation || !form.department || !form.salary) {
        this.formError = "Please fill in all fields.";
        this.$nextTick(() => shakeElement(this.$refs.modalPanel));
        return;
      }
      const nextId = Math.max(0, ...this.employees.map((e) => e.id)) + 1;
      const initials = form.name
        .split(" ")
        .map((p) => p[0])
        .join("")
        .slice(0, 2)
        .toUpperCase();
      this.employees.push({
        id: nextId,
        name: form.name,
        designation: form.designation,
        department: form.department,
        experience_years: Number(form.experience_years) || 0,
        salary: Number(form.salary),
        initials,
      });
      this.formError = "";
      this.$nextTick(() => {
        const rows = this.$refs.tbody.querySelectorAll("tr");
        animateRowIn(rows[rows.length - 1]);
      });
      window.dispatchEvent(new CustomEvent("toast", { detail: { message: `${form.name} added.` } }));
      this.closeModal();
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
