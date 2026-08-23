# BusCom Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the frontend of the BusCom app — login, HR dashboard, and employee self-service screens — with mocked employee/salary/payslip data and polished, restrained motion design.

**Architecture:** A single Django project (`buscom`) with one app (`dashboard`) serving server-rendered templates. Tailwind CSS (standalone CLI, no Node) handles styling, Alpine.js handles client-side state, and GSAP handles motion. A custom `User` model adds a `role` field (`hr`/`employee`) driving role-based views and navigation. Employee/salary/payslip data is mocked Python data (or client-side Alpine state for in-session additions) — no real persistence yet.

**Tech Stack:** Python 3 + Django 5, Tailwind CSS (standalone CLI binary), Alpine.js (CDN), GSAP (CDN), SQLite (auth only).

## Global Constraints

- Backend: Django, server-rendered templates (no REST/JSON API layer for this phase)
- Styling: Tailwind CSS via the standalone CLI binary — no Node/npm dependency
- Interactivity: Alpine.js
- Motion: GSAP — used to clarify state changes, kept restrained, not decorative
- Database: SQLite, used only for Django auth (`User` model) at this stage
- Custom `User` model with a `role` field (`hr` / `employee`) drives navigation/permissions
- Employee, salary, and payslip data are mocked — no real persistence in this phase
- Testing: Django smoke tests (route returns 200, correct template used); motion/visual correctness is verified manually in-browser, not by automated tests

---

## File Structure

```
BusCom/
├── manage.py
├── requirements.txt
├── tailwind.config.js
├── .gitignore
├── buscom/                      # Django project config
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
└── dashboard/                   # Single Django app for this phase
    ├── __init__.py
    ├── apps.py
    ├── models.py                # Custom User model (role field)
    ├── views.py
    ├── urls.py
    ├── mock_data.py             # Mocked employees + payslips
    ├── tests.py
    ├── migrations/
    │   ├── 0001_initial.py
    │   └── 0002_seed_demo_users.py
    ├── static/dashboard/
    │   ├── css/
    │   │   ├── input.css        # Tailwind source
    │   │   └── output.css       # Tailwind build output (committed)
    │   └── js/
    │       ├── motion.js        # GSAP animation helpers
    │       └── app.js           # Alpine.js components
    └── templates/
        ├── 404.html
        ├── 500.html
        └── dashboard/
            ├── base.html
            ├── login.html
            ├── hr_dashboard.html
            ├── employee_self_service.html
            ├── payslip_detail.html
            ├── empty_state.html
            └── partials/
                ├── sidebar.html
                ├── topbar.html
                └── employee_modal.html
```

---

### Task 1: Django Project & App Scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `manage.py`, `buscom/settings.py`, `buscom/urls.py`, `buscom/wsgi.py`, `buscom/asgi.py` (via `django-admin startproject`)
- Create: `dashboard/` app files (via `manage.py startapp`)
- Create: `dashboard/urls.py`
- Modify: `dashboard/views.py`
- Modify: `buscom/settings.py` (add `dashboard` to `INSTALLED_APPS`)
- Modify: `buscom/urls.py` (include `dashboard.urls`)
- Create: `dashboard/tests.py`
- Create: `.gitignore`

**Interfaces:**
- Produces: URL name `"root"` → `GET /` returning HTTP 200. Later tasks (Task 5) will replace the view behind this URL with real redirect logic, but the URL name and route stay the same.

- [ ] **Step 1: Create virtualenv and install Django**

```bash
cd /home/dextro/Desktop/BusCom
python3 -m venv venv
source venv/bin/activate
pip install "Django>=5.0,<6.0"
pip freeze > requirements.txt
```

- [ ] **Step 2: Scaffold the Django project and app**

```bash
django-admin startproject buscom .
python manage.py startapp dashboard
```

- [ ] **Step 3: Register the app**

In `buscom/settings.py`, add `"dashboard"` to `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "dashboard",
]
```

- [ ] **Step 4: Write the failing smoke test**

Create `dashboard/tests.py`:

```python
from django.test import TestCase
from django.urls import reverse


class RootRouteTests(TestCase):
    def test_root_route_returns_ok(self):
        response = self.client.get(reverse("root"))
        self.assertEqual(response.status_code, 200)
```

- [ ] **Step 5: Run test to verify it fails**

Run: `python manage.py test dashboard -v 2`
Expected: FAIL — `NoReverseMatch` (URL name `"root"` doesn't exist yet)

- [ ] **Step 6: Implement the minimal root view and URL**

Create `dashboard/urls.py`:

```python
from django.urls import path

from . import views

urlpatterns = [
    path("", views.root_view, name="root"),
]
```

In `dashboard/views.py`:

```python
from django.http import HttpResponse


def root_view(request):
    return HttpResponse("OK")
```

In `buscom/urls.py`:

```python
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("dashboard.urls")),
]
```

- [ ] **Step 7: Run test to verify it passes**

Run: `python manage.py test dashboard -v 2`
Expected: PASS

- [ ] **Step 8: Add `.gitignore`**

Create `.gitignore`:

```
venv/
__pycache__/
*.pyc
db.sqlite3
/tailwindcss
```

- [ ] **Step 9: Commit**

```bash
git add manage.py buscom dashboard requirements.txt .gitignore
git commit -m "chore: scaffold Django project and dashboard app"
```

---

### Task 2: Custom User Model with Role + Demo User Seed

**Files:**
- Modify: `dashboard/models.py`
- Modify: `buscom/settings.py` (`AUTH_USER_MODEL`)
- Create: `dashboard/migrations/0001_initial.py` (via `makemigrations`)
- Create: `dashboard/migrations/0002_seed_demo_users.py`
- Modify: `dashboard/tests.py`

**Interfaces:**
- Produces: `dashboard.models.User` with `User.Role.HR` (`"hr"`) and `User.Role.EMPLOYEE` (`"employee"`) choices, and a `role` field. Two demo accounts seeded by migration: username `hr_admin` (password `buscom-hr-2026`, role `hr`, email `hr@buscom.test`) and username `amara_okafor` (password `buscom-emp-2026`, role `employee`, email `amara.okafor@buscom.test`).
- Consumes: nothing outside this task.

- [ ] **Step 1: Write the failing test for the role field**

Append to `dashboard/tests.py`:

```python
from django.contrib.auth import get_user_model


class UserRoleTests(TestCase):
    def test_user_has_role_field_defaulting_to_employee(self):
        User = get_user_model()
        user = User.objects.create_user(username="jdoe", password="x")
        self.assertEqual(user.role, User.Role.EMPLOYEE)

    def test_demo_users_are_seeded(self):
        User = get_user_model()
        hr = User.objects.get(username="hr_admin")
        employee = User.objects.get(username="amara_okafor")
        self.assertEqual(hr.role, User.Role.HR)
        self.assertEqual(employee.role, User.Role.EMPLOYEE)
        self.assertEqual(employee.email, "amara.okafor@buscom.test")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test dashboard -v 2`
Expected: FAIL — `AUTH_USER_MODEL` still points at `auth.User`, which has no `role` field / `Role` attribute

- [ ] **Step 3: Define the custom User model**

In `dashboard/models.py`:

```python
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        HR = "hr", "HR"
        EMPLOYEE = "employee", "Employee"

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.EMPLOYEE)
```

In `buscom/settings.py`, add:

```python
AUTH_USER_MODEL = "dashboard.User"
```

- [ ] **Step 4: Generate the initial migration**

```bash
python manage.py makemigrations dashboard
```

- [ ] **Step 5: Write the demo user seed migration**

Create `dashboard/migrations/0002_seed_demo_users.py`:

```python
from django.db import migrations


def seed_demo_users(apps, schema_editor):
    User = apps.get_model("dashboard", "User")
    if not User.objects.filter(username="hr_admin").exists():
        User.objects.create_user(
            username="hr_admin",
            email="hr@buscom.test",
            password="buscom-hr-2026",
            role="hr",
            first_name="Priya",
            last_name="Sharma",
        )
    if not User.objects.filter(username="amara_okafor").exists():
        User.objects.create_user(
            username="amara_okafor",
            email="amara.okafor@buscom.test",
            password="buscom-emp-2026",
            role="employee",
            first_name="Amara",
            last_name="Okafor",
        )


def unseed_demo_users(apps, schema_editor):
    User = apps.get_model("dashboard", "User")
    User.objects.filter(username__in=["hr_admin", "amara_okafor"]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("dashboard", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_demo_users, unseed_demo_users),
    ]
```

- [ ] **Step 6: Apply migrations to the dev database**

```bash
python manage.py migrate
```

- [ ] **Step 7: Run test to verify it passes**

Run: `python manage.py test dashboard -v 2`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add dashboard/models.py dashboard/migrations dashboard/tests.py buscom/settings.py
git commit -m "feat: add custom User model with role field and seed demo users"
```

---

### Task 3: Tailwind CSS Setup (Standalone CLI)

**Files:**
- Create: `tailwind.config.js`
- Create: `dashboard/static/dashboard/css/input.css`
- Create: `dashboard/static/dashboard/css/output.css` (build output)

**Interfaces:**
- Produces: static asset `dashboard/css/output.css`, referenced by templates from Task 4 onward via `{% static 'dashboard/css/output.css' %}`.

- [ ] **Step 1: Download the Tailwind standalone CLI binary**

```bash
cd /home/dextro/Desktop/BusCom
curl -sLo tailwindcss https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-linux-x64
chmod +x tailwindcss
```

- [ ] **Step 2: Configure Tailwind's content scan paths**

Create `tailwind.config.js`:

```js
module.exports = {
  content: ["./dashboard/templates/**/*.html"],
  darkMode: "class",
  theme: {
    extend: {},
  },
  plugins: [],
};
```

- [ ] **Step 3: Write the Tailwind source file**

Create `dashboard/static/dashboard/css/input.css`:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

[x-cloak] {
  display: none !important;
}
```

- [ ] **Step 4: Build the CSS output**

```bash
mkdir -p dashboard/static/dashboard/css
./tailwindcss -i ./dashboard/static/dashboard/css/input.css -o ./dashboard/static/dashboard/css/output.css --minify
```

- [ ] **Step 5: Verify the build output exists and is non-trivial**

Run: `wc -l dashboard/static/dashboard/css/output.css`
Expected: a non-empty, minified CSS file (hundreds+ of lines minified onto few lines)

- [ ] **Step 6: Commit**

```bash
git add tailwind.config.js dashboard/static/dashboard/css/input.css dashboard/static/dashboard/css/output.css
git commit -m "chore: add Tailwind CSS build via standalone CLI"
```

*Note: re-run the Step 4 build command any time template class names change, throughout later tasks.*

---

### Task 4: Shared App Shell (base.html, sidebar, topbar, theme toggle, page transition)

**Files:**
- Create: `dashboard/templates/dashboard/base.html`
- Create: `dashboard/templates/dashboard/partials/sidebar.html`
- Create: `dashboard/templates/dashboard/partials/topbar.html`
- Create: `dashboard/static/dashboard/js/motion.js`
- Create: `dashboard/static/dashboard/js/app.js`

**Interfaces:**
- Produces: `base.html` with blocks `{% block title %}`, `{% block content %}` (authenticated shell) and `{% block guest_content %}` (unauthenticated pages like login). Global JS functions in `motion.js`: `fadeInPage(el)`, `staggerRows(container)`, `animateRowIn(row)`, `animateCountUp(el, target, options)`, `animateModalIn(el)`, `animateModalOut(el, onComplete)`, `animateToastIn(el)`, `shakeElement(el)`.
- Consumes: `dashboard/css/output.css` from Task 3.

- [ ] **Step 1: Write motion.js**

Create `dashboard/static/dashboard/js/motion.js`:

```js
function fadeInPage(el) {
  gsap.fromTo(el, { opacity: 0, y: 12 }, { opacity: 1, y: 0, duration: 0.35, ease: "power2.out" });
}

function staggerRows(container) {
  if (!container) return;
  const rows = container.querySelectorAll("tr");
  gsap.fromTo(rows, { opacity: 0, y: 8 }, { opacity: 1, y: 0, duration: 0.3, stagger: 0.05, ease: "power2.out" });
}

function animateRowIn(row) {
  if (!row) return;
  gsap.fromTo(
    row,
    { opacity: 0, backgroundColor: "rgba(99,102,241,0.15)" },
    { opacity: 1, backgroundColor: "rgba(0,0,0,0)", duration: 0.6, ease: "power2.out" }
  );
}

function animateCountUp(el, target, options = {}) {
  if (!el) return;
  const { prefix = "", decimals = 0 } = options;
  const counter = { value: 0 };
  gsap.to(counter, {
    value: target,
    duration: 1,
    ease: "power1.out",
    onUpdate: () => {
      el.textContent = prefix + counter.value.toLocaleString(undefined, {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
      });
    },
  });
}

function animateModalIn(el) {
  if (!el) return;
  gsap.fromTo(el, { opacity: 0, scale: 0.95 }, { opacity: 1, scale: 1, duration: 0.2, ease: "power2.out" });
}

function animateModalOut(el, onComplete) {
  if (!el) return onComplete && onComplete();
  gsap.to(el, { opacity: 0, scale: 0.95, duration: 0.15, ease: "power1.in", onComplete });
}

function animateToastIn(el) {
  if (!el) return;
  gsap.fromTo(el, { opacity: 0, x: 40 }, { opacity: 1, x: 0, duration: 0.3, ease: "power2.out" });
}

function shakeElement(el) {
  if (!el) return;
  gsap.fromTo(el, { x: -6 }, { x: 0, duration: 0.4, ease: "elastic.out(1, 0.3)" });
}
```

- [ ] **Step 2: Write app.js with the theme toggle helper (other components added in later tasks)**

Create `dashboard/static/dashboard/js/app.js`:

```js
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
```

- [ ] **Step 3: Write the sidebar partial**

Create `dashboard/templates/dashboard/partials/sidebar.html`:

```html
<aside class="w-60 shrink-0 bg-white dark:bg-slate-800 border-r border-slate-200 dark:border-slate-700 flex flex-col print:hidden">
  <div class="px-5 py-4 text-lg font-semibold">BusCom</div>
  <nav class="flex-1 px-3 space-y-1">
    {% if user.role == "hr" %}
      <a href="{% url 'hr_dashboard' %}" class="block rounded-lg px-3 py-2 text-sm font-medium hover:bg-slate-100 dark:hover:bg-slate-700 transition">Dashboard</a>
    {% else %}
      <a href="{% url 'employee_self_service' %}" class="block rounded-lg px-3 py-2 text-sm font-medium hover:bg-slate-100 dark:hover:bg-slate-700 transition">My Profile</a>
    {% endif %}
  </nav>
</aside>
```

- [ ] **Step 4: Write the topbar partial**

Create `dashboard/templates/dashboard/partials/topbar.html`:

```html
<header class="h-16 flex items-center justify-end px-6 border-b border-slate-200 dark:border-slate-700 print:hidden">
  <div class="flex items-center gap-4" x-data="{ open: false }">
    <button @click="dark = !dark" type="button" class="text-sm px-2 py-1 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition">
      <span x-show="!dark">Dark mode</span>
      <span x-show="dark" x-cloak>Light mode</span>
    </button>
    <div class="relative">
      <button @click="open = !open" type="button" class="flex items-center gap-2 text-sm font-medium">
        {{ user.first_name|default:user.username }}
      </button>
      <div x-show="open" @click.outside="open = false" x-cloak
           class="absolute right-0 mt-2 w-40 rounded-lg bg-white dark:bg-slate-800 shadow-lg border border-slate-200 dark:border-slate-700 py-1">
        <a href="{% url 'logout' %}" class="block px-4 py-2 text-sm hover:bg-slate-100 dark:hover:bg-slate-700 transition">Log out</a>
      </div>
    </div>
  </div>
</header>
```

- [ ] **Step 5: Write base.html**

Create `dashboard/templates/dashboard/base.html`:

```html
{% load static %}
<!DOCTYPE html>
<html lang="en"
      x-data="{ dark: localStorage.getItem('theme') === 'dark' }"
      x-init="$watch('dark', v => localStorage.setItem('theme', v ? 'dark' : 'light'))"
      :class="{ 'dark': dark }">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{% block title %}BusCom{% endblock %}</title>
  <link rel="stylesheet" href="{% static 'dashboard/css/output.css' %}">
  <script src="https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/gsap.min.js"></script>
  <script src="{% static 'dashboard/js/motion.js' %}"></script>
  <script src="{% static 'dashboard/js/app.js' %}"></script>
  <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.14.1/dist/cdn.min.js"></script>
</head>
<body class="bg-slate-50 dark:bg-slate-900 text-slate-900 dark:text-slate-100 min-h-screen">
  {% if user.is_authenticated %}
  <div class="flex h-screen overflow-hidden">
    {% include "dashboard/partials/sidebar.html" %}
    <div class="flex-1 flex flex-col overflow-hidden">
      {% include "dashboard/partials/topbar.html" %}
      <main class="flex-1 overflow-y-auto p-6" x-data x-init="fadeInPage($el)">
        {% block content %}{% endblock %}
      </main>
    </div>
  </div>
  <div x-data="toast()" @toast.window="add($event.detail.message)"
       class="fixed top-4 right-4 space-y-2 z-50 print:hidden">
    <template x-for="t in items" :key="t.id">
      <div :data-toast-id="t.id"
           class="rounded-lg bg-slate-900 text-white text-sm px-4 py-2 shadow-lg">
        <span x-text="t.message"></span>
      </div>
    </template>
  </div>
  {% else %}
  <main class="flex items-center justify-center min-h-screen p-6">
    {% block guest_content %}{% endblock %}
  </main>
  {% endif %}
</body>
</html>
```

- [ ] **Step 6: Manually verify the shell renders**

Run: `python manage.py runserver`, visit `http://127.0.0.1:8000/` while not logged in.
Expected: blank guest area (no `guest_content` block yet), no console errors, no Tailwind/Alpine/GSAP load errors in devtools.

- [ ] **Step 7: Commit**

```bash
git add dashboard/templates/dashboard/base.html dashboard/templates/dashboard/partials dashboard/static/dashboard/js
git commit -m "feat: add shared app shell with theme toggle and motion helpers"
```

---

### Task 5: Login, Role-Based Redirect, Logout

**Files:**
- Modify: `dashboard/views.py`
- Modify: `dashboard/urls.py`
- Create: `dashboard/templates/dashboard/login.html`
- Modify: `buscom/settings.py` (`LOGIN_URL`)
- Modify: `dashboard/tests.py`

**Interfaces:**
- Consumes: `User.Role.HR` / `User.Role.EMPLOYEE` from Task 2; `fadeInPage`, `shakeElement` from Task 4's `motion.js`; `base.html`'s `guest_content` block.
- Produces: URL names `"login"`, `"logout"`; view `RoleLoginView` redirecting HR users to `hr_dashboard` and employees to `employee_self_service` (both routes added in Tasks 7/9 — until then, redirect targets are literal `/dashboard/` and `/me/` strings, made into named routes once those tasks exist). Root view (`"root"`, from Task 1) becomes `root_redirect`: unauthenticated → `login`, HR → `/dashboard/`, employee → `/me/`.

- [ ] **Step 1: Write the failing tests**

Replace the `RootRouteTests` test in `dashboard/tests.py` with:

```python
class AuthFlowTests(TestCase):
    def test_root_redirects_anonymous_user_to_login(self):
        response = self.client.get(reverse("root"))
        self.assertRedirects(response, reverse("login"))

    def test_hr_login_redirects_to_dashboard_path(self):
        self.client.login(username="hr_admin", password="buscom-hr-2026")
        response = self.client.get(reverse("root"))
        self.assertRedirects(response, "/dashboard/")

    def test_employee_login_redirects_to_self_service_path(self):
        self.client.login(username="amara_okafor", password="buscom-emp-2026")
        response = self.client.get(reverse("root"))
        self.assertRedirects(response, "/me/")

    def test_login_page_renders(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/login.html")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test dashboard -v 2`
Expected: FAIL — `root_view` still returns `"OK"` instead of redirecting; `"login"` URL doesn't exist

- [ ] **Step 3: Implement the views**

Replace the contents of `dashboard/views.py`:

```python
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect

from .models import User


class RoleLoginView(auth_views.LoginView):
    template_name = "dashboard/login.html"

    def get_success_url(self):
        if self.request.user.role == User.Role.HR:
            return "/dashboard/"
        return "/me/"


def root_redirect(request):
    if not request.user.is_authenticated:
        return redirect("login")
    if request.user.role == User.Role.HR:
        return redirect("/dashboard/")
    return redirect("/me/")
```

- [ ] **Step 4: Wire up urls**

Replace `dashboard/urls.py`:

```python
from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("", views.root_redirect, name="root"),
    path("login/", views.RoleLoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="login"), name="logout"),
]
```

- [ ] **Step 5: Set `LOGIN_URL` in settings**

In `buscom/settings.py`, add:

```python
LOGIN_URL = "login"
```

- [ ] **Step 6: Write the login template**

Create `dashboard/templates/dashboard/login.html`:

```html
{% extends "dashboard/base.html" %}
{% block title %}Sign in — BusCom{% endblock %}
{% block guest_content %}
<div class="w-full max-w-sm bg-white dark:bg-slate-800 rounded-xl shadow p-8"
     x-data x-init="fadeInPage($el); {% if form.errors %}shakeElement($el){% endif %}">
  <h1 class="text-2xl font-semibold mb-1">BusCom</h1>
  <p class="text-slate-500 text-sm mb-6">Sign in to manage your payroll.</p>
  {% if form.errors %}
    <p class="text-red-500 text-sm mb-4">Invalid username or password.</p>
  {% endif %}
  <form method="post">
    {% csrf_token %}
    <label class="block text-sm font-medium mb-1" for="id_username">Username</label>
    <input class="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-transparent px-3 py-2 mb-4 focus:outline-none focus:ring-2 focus:ring-indigo-500"
           type="text" name="username" id="id_username" required>
    <label class="block text-sm font-medium mb-1" for="id_password">Password</label>
    <input class="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-transparent px-3 py-2 mb-6 focus:outline-none focus:ring-2 focus:ring-indigo-500"
           type="password" name="password" id="id_password" required>
    <button class="w-full rounded-lg bg-indigo-600 hover:bg-indigo-500 active:scale-[0.98] transition text-white font-medium py-2" type="submit">
      Sign in
    </button>
  </form>
</div>
{% endblock %}
```

- [ ] **Step 7: Rebuild Tailwind CSS**

```bash
./tailwindcss -i ./dashboard/static/dashboard/css/input.css -o ./dashboard/static/dashboard/css/output.css --minify
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `python manage.py test dashboard -v 2`
Expected: PASS

- [ ] **Step 9: Manually verify in browser**

Run: `python manage.py runserver`, visit `http://127.0.0.1:8000/`, log in as `hr_admin` / `buscom-hr-2026`.
Expected: redirected toward `/dashboard/` (404 is fine — that route is built in Task 7); log out and try `amara_okafor` / `buscom-emp-2026`, confirm redirect toward `/me/`. Try a wrong password and confirm the form shakes and shows an error.

- [ ] **Step 10: Commit**

```bash
git add dashboard/views.py dashboard/urls.py dashboard/templates/dashboard/login.html buscom/settings.py dashboard/tests.py dashboard/static/dashboard/css/output.css
git commit -m "feat: add login, logout, and role-based redirect"
```

---

### Task 6: Mock Data Module

**Files:**
- Create: `dashboard/mock_data.py`

**Interfaces:**
- Produces: `EMPLOYEES` (list of dicts, keys: `id`, `name`, `email`, `designation`, `department`, `experience_years`, `salary`, `initials`) and `PAYSLIPS` (list of dicts, keys: `id`, `employee_id`, `period`, `gross`, `deductions`, `net`, `breakdown` — a list of `{"label": str, "amount": number}`). `EMPLOYEES[0]["email"]` matches the demo employee user's email (`amara.okafor@buscom.test`) from Task 2.
- Consumes: nothing (pure data module, no test required — used and exercised indirectly by Tasks 7, 9, 10's view tests).

- [ ] **Step 1: Write the mock data module**

Create `dashboard/mock_data.py`:

```python
EMPLOYEES = [
    {
        "id": 1,
        "name": "Amara Okafor",
        "email": "amara.okafor@buscom.test",
        "designation": "Senior Backend Engineer",
        "department": "Engineering",
        "experience_years": 6,
        "salary": 95000,
        "initials": "AO",
    },
    {
        "id": 2,
        "name": "Diego Martins",
        "email": "diego.martins@buscom.test",
        "designation": "Product Designer",
        "department": "Design",
        "experience_years": 4,
        "salary": 78000,
        "initials": "DM",
    },
    {
        "id": 3,
        "name": "Sara Lindqvist",
        "email": "sara.lindqvist@buscom.test",
        "designation": "HR Business Partner",
        "department": "People",
        "experience_years": 8,
        "salary": 82000,
        "initials": "SL",
    },
    {
        "id": 4,
        "name": "Kenji Watanabe",
        "email": "kenji.watanabe@buscom.test",
        "designation": "Junior Frontend Engineer",
        "department": "Engineering",
        "experience_years": 1,
        "salary": 58000,
        "initials": "KW",
    },
    {
        "id": 5,
        "name": "Fatima Rahman",
        "email": "fatima.rahman@buscom.test",
        "designation": "Finance Analyst",
        "department": "Finance",
        "experience_years": 3,
        "salary": 67000,
        "initials": "FR",
    },
]

PAYSLIPS = [
    {
        "id": 1,
        "employee_id": 1,
        "period": "June 2026",
        "gross": 8300.00,
        "deductions": 1200.00,
        "net": 7100.00,
        "breakdown": [
            {"label": "Base Salary", "amount": 7916.67},
            {"label": "Performance Bonus", "amount": 383.33},
            {"label": "Tax", "amount": -950.00},
            {"label": "Insurance", "amount": -250.00},
        ],
    },
    {
        "id": 2,
        "employee_id": 1,
        "period": "July 2026",
        "gross": 8300.00,
        "deductions": 1150.00,
        "net": 7150.00,
        "breakdown": [
            {"label": "Base Salary", "amount": 7916.67},
            {"label": "Performance Bonus", "amount": 383.33},
            {"label": "Tax", "amount": -900.00},
            {"label": "Insurance", "amount": -250.00},
        ],
    },
]
```

- [ ] **Step 2: Commit**

```bash
git add dashboard/mock_data.py
git commit -m "feat: add mocked employee and payslip data"
```

---

### Task 7: HR Dashboard — Stat Cards, Employee Directory, Search, Skeleton Loader

**Files:**
- Modify: `dashboard/views.py`
- Modify: `dashboard/urls.py`
- Create: `dashboard/templates/dashboard/hr_dashboard.html`
- Modify: `dashboard/static/dashboard/js/app.js`
- Modify: `dashboard/tests.py`

**Interfaces:**
- Consumes: `EMPLOYEES` from `dashboard/mock_data.py` (Task 6); `User.Role.HR` (Task 2); `staggerRows`, `animateCountUp`, `animateRowIn` from `motion.js` (Task 4).
- Produces: URL name `"hr_dashboard"` → `GET /dashboard/`, HR-only. Alpine component `employeeDirectory(initialEmployees)` in `app.js` with reactive state `employees`, `query`, `loading`, computed `filtered`, and method `addEmployee(form)` (used by Task 8's modal).

- [ ] **Step 1: Write the failing tests**

Append to `dashboard/tests.py`:

```python
class HrDashboardTests(TestCase):
    def test_requires_login(self):
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 302)

    def test_hr_user_can_view_dashboard(self):
        self.client.login(username="hr_admin", password="buscom-hr-2026")
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/hr_dashboard.html")
        self.assertContains(response, "Amara Okafor")

    def test_employee_user_is_redirected_away_from_dashboard(self):
        self.client.login(username="amara_okafor", password="buscom-emp-2026")
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 302)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test dashboard -v 2`
Expected: FAIL — `/dashboard/` route doesn't exist (404)

- [ ] **Step 3: Implement the view**

Append to `dashboard/views.py`:

```python
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render

from .mock_data import EMPLOYEES


def _is_hr(user):
    return user.is_authenticated and user.role == User.Role.HR


@login_required
@user_passes_test(_is_hr, login_url="/me/")
def hr_dashboard(request):
    headcount = len(EMPLOYEES)
    total_payroll = sum(e["salary"] for e in EMPLOYEES)
    avg_salary = round(total_payroll / headcount, 2) if headcount else 0
    return render(request, "dashboard/hr_dashboard.html", {
        "employees": EMPLOYEES,
        "headcount": headcount,
        "total_payroll": total_payroll,
        "avg_salary": avg_salary,
    })
```

- [ ] **Step 4: Wire up the URL**

In `dashboard/urls.py`, add to `urlpatterns`:

```python
    path("dashboard/", views.hr_dashboard, name="hr_dashboard"),
```

- [ ] **Step 5: Add the employeeDirectory Alpine component**

Replace the entire contents of `dashboard/static/dashboard/js/app.js` with the following. This keeps the `toast` component from Task 4 and adds `employeeDirectory` as a second registration inside the same `alpine:init` callback:

```js
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
```

- [ ] **Step 6: Write the HR dashboard template**

Create `dashboard/templates/dashboard/hr_dashboard.html`:

```html
{% extends "dashboard/base.html" %}
{% load static %}
{% block title %}Dashboard — BusCom{% endblock %}
{% block content %}
{{ employees|json_script:"employees-data" }}
<div x-data="employeeDirectory(JSON.parse(document.getElementById('employees-data').textContent))">
  <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
    <div class="rounded-xl bg-white dark:bg-slate-800 shadow p-5" x-data x-init="animateCountUp($el.querySelector('.stat-value'), {{ headcount }})">
      <p class="text-sm text-slate-500">Headcount</p>
      <p class="stat-value text-3xl font-semibold mt-1">0</p>
    </div>
    <div class="rounded-xl bg-white dark:bg-slate-800 shadow p-5" x-data x-init="animateCountUp($el.querySelector('.stat-value'), {{ total_payroll }}, { prefix: '$' })">
      <p class="text-sm text-slate-500">Total Payroll</p>
      <p class="stat-value text-3xl font-semibold mt-1">$0</p>
    </div>
    <div class="rounded-xl bg-white dark:bg-slate-800 shadow p-5" x-data x-init="animateCountUp($el.querySelector('.stat-value'), {{ avg_salary }}, { prefix: '$' })">
      <p class="text-sm text-slate-500">Average Salary</p>
      <p class="stat-value text-3xl font-semibold mt-1">$0</p>
    </div>
  </div>

  <div class="rounded-xl bg-white dark:bg-slate-800 shadow p-5">
    <div class="flex items-center justify-between mb-4">
      <input x-model="query" type="text" placeholder="Search employees..."
             class="w-64 rounded-lg border border-slate-300 dark:border-slate-600 bg-transparent px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
      <button @click="showModal = true; $nextTick(() => animateModalIn($refs.modalPanel))" type="button"
              class="rounded-lg bg-indigo-600 hover:bg-indigo-500 active:scale-[0.98] transition text-white text-sm font-medium px-4 py-1.5">
        Add Employee
      </button>
    </div>

    <template x-if="loading">
      <div class="space-y-2 animate-pulse">
        <div class="h-10 bg-slate-100 dark:bg-slate-700 rounded"></div>
        <div class="h-10 bg-slate-100 dark:bg-slate-700 rounded"></div>
        <div class="h-10 bg-slate-100 dark:bg-slate-700 rounded"></div>
      </div>
    </template>

    <table class="w-full text-sm" x-show="!loading">
      <thead>
        <tr class="text-left text-slate-500 border-b border-slate-200 dark:border-slate-700">
          <th class="py-2">Name</th>
          <th class="py-2">Designation</th>
          <th class="py-2">Department</th>
          <th class="py-2">Experience</th>
          <th class="py-2 text-right">Salary</th>
        </tr>
      </thead>
      <tbody x-ref="tbody">
        <template x-for="employee in filtered" :key="employee.id">
          <tr class="border-b border-slate-100 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700/50 transition">
            <td class="py-2 flex items-center gap-2">
              <span class="w-7 h-7 rounded-full bg-indigo-100 dark:bg-indigo-900 text-indigo-600 dark:text-indigo-300 text-xs flex items-center justify-center font-medium" x-text="employee.initials"></span>
              <span x-text="employee.name"></span>
            </td>
            <td class="py-2" x-text="employee.designation"></td>
            <td class="py-2" x-text="employee.department"></td>
            <td class="py-2" x-text="employee.experience_years + ' yrs'"></td>
            <td class="py-2 text-right" x-text="'$' + employee.salary.toLocaleString()"></td>
          </tr>
        </template>
      </tbody>
    </table>
  </div>

  {% include "dashboard/partials/employee_modal.html" %}
</div>
{% endblock %}
```

*(This template includes `dashboard/partials/employee_modal.html`, which is created in Task 8 — the `{% include %}` will 500 until Task 8 lands. If verifying Task 7 in isolation, temporarily comment out that include line.)*

- [ ] **Step 7: Rebuild Tailwind CSS**

```bash
./tailwindcss -i ./dashboard/static/dashboard/css/input.css -o ./dashboard/static/dashboard/css/output.css --minify
```

- [ ] **Step 8: Run tests to verify they pass** (temporarily comment out the `employee_modal.html` include first, since Task 8 hasn't created it yet)

Run: `python manage.py test dashboard -v 2`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add dashboard/views.py dashboard/urls.py dashboard/templates/dashboard/hr_dashboard.html dashboard/static/dashboard/js/app.js dashboard/tests.py dashboard/static/dashboard/css/output.css
git commit -m "feat: add HR dashboard with stat cards, searchable directory, and skeleton loader"
```

---

### Task 8: Add/Edit Employee Modal + Toast Notifications

**Files:**
- Create: `dashboard/templates/dashboard/partials/employee_modal.html`
- Modify: `dashboard/static/dashboard/js/app.js` (extend `employeeDirectory` with modal + add-employee logic)
- Modify: `dashboard/templates/dashboard/hr_dashboard.html` (uncomment the include if it was commented out in Task 7)

**Interfaces:**
- Consumes: `employeeDirectory` component state (`showModal`, `formError`, `employees`) from Task 7; `animateModalIn`, `animateModalOut`, `shakeElement`, `animateRowIn` from `motion.js` (Task 4); the global `toast` component from `base.html` (Task 4), triggered via a `window` `CustomEvent("toast", { detail: { message } })`.
- Produces: working "Add Employee" flow — new employees appended client-side to the directory table with an entrance animation, plus a toast confirmation. No backend persistence (per spec).

- [ ] **Step 1: Add modal + add-employee logic to `employeeDirectory`**

Replace the entire contents of `dashboard/static/dashboard/js/app.js` (the file created in Task 4 and updated in Task 7) with the following — `employeeDirectory` gains `openModal`/`closeModal`/`addEmployee`, `toast` is unchanged:

```js
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
```

- [ ] **Step 2: Write the modal partial**

Create `dashboard/templates/dashboard/partials/employee_modal.html`:

```html
<div x-show="showModal" x-cloak
     class="fixed inset-0 bg-black/40 flex items-center justify-center z-40 print:hidden"
     @keydown.escape.window="showModal && closeModal()">
  <div x-ref="modalPanel"
       @click.outside="closeModal()"
       class="w-full max-w-md bg-white dark:bg-slate-800 rounded-xl shadow-lg p-6">
    <h2 class="text-lg font-semibold mb-4">Add Employee</h2>
    <template x-if="formError">
      <p class="text-red-500 text-sm mb-3" x-text="formError"></p>
    </template>
    <form @submit.prevent="addEmployee({
            name: $refs.name.value,
            designation: $refs.designation.value,
            department: $refs.department.value,
            experience_years: $refs.experience.value,
            salary: $refs.salary.value,
          })">
      <div class="space-y-3 mb-5">
        <input x-ref="name" type="text" placeholder="Full name"
               class="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-transparent px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
        <input x-ref="designation" type="text" placeholder="Designation"
               class="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-transparent px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
        <input x-ref="department" type="text" placeholder="Department"
               class="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-transparent px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
        <input x-ref="experience" type="number" min="0" placeholder="Years of experience"
               class="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-transparent px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
        <input x-ref="salary" type="number" min="0" placeholder="Salary"
               class="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-transparent px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
      </div>
      <div class="flex justify-end gap-2">
        <button type="button" @click="closeModal()"
                class="rounded-lg px-4 py-1.5 text-sm border border-slate-300 dark:border-slate-600 hover:bg-slate-100 dark:hover:bg-slate-700 transition">
          Cancel
        </button>
        <button type="submit"
                class="rounded-lg bg-indigo-600 hover:bg-indigo-500 active:scale-[0.98] transition text-white text-sm font-medium px-4 py-1.5">
          Add
        </button>
      </div>
    </form>
  </div>
</div>
```

- [ ] **Step 3: Wire the "Add Employee" button to `openModal()`**

In `dashboard/templates/dashboard/hr_dashboard.html`, replace the button's `@click`:

```html
      <button @click="openModal()" type="button"
              class="rounded-lg bg-indigo-600 hover:bg-indigo-500 active:scale-[0.98] transition text-white text-sm font-medium px-4 py-1.5">
        Add Employee
      </button>
```

Uncomment (or add back) the modal include at the bottom of the same file if it was disabled in Task 7:

```html
  {% include "dashboard/partials/employee_modal.html" %}
```

- [ ] **Step 4: Rebuild Tailwind CSS**

```bash
./tailwindcss -i ./dashboard/static/dashboard/css/input.css -o ./dashboard/static/dashboard/css/output.css --minify
```

- [ ] **Step 5: Run the existing test suite to confirm no regressions**

Run: `python manage.py test dashboard -v 2`
Expected: PASS (this task is UI-only client-side behavior; no new Django-level test is meaningful here)

- [ ] **Step 6: Manually verify in browser**

Log in as `hr_admin`, click "Add Employee", submit with a field blank — confirm the modal shakes and shows an error. Fill all fields and submit — confirm the modal closes, a new row animates into the table, and a toast appears bottom-right... top-right and disappears after ~3.5s.

- [ ] **Step 7: Commit**

```bash
git add dashboard/templates/dashboard/partials/employee_modal.html dashboard/templates/dashboard/hr_dashboard.html dashboard/static/dashboard/js/app.js dashboard/static/dashboard/css/output.css
git commit -m "feat: add employee modal with client-side add flow and toast notifications"
```

---

### Task 9: Payslip Detail View (Itemized Breakdown, Print Layout)

*(Ordered before the Employee Self-Service task because that task's template links to `payslip_detail` — building this first means every task's own test suite is green in isolation, with no forward references.)*

**Files:**
- Modify: `dashboard/views.py`
- Modify: `dashboard/urls.py`
- Create: `dashboard/templates/dashboard/payslip_detail.html`
- Create: `dashboard/templates/dashboard/empty_state.html`
- Modify: `dashboard/tests.py`

**Interfaces:**
- Consumes: `PAYSLIPS` from `dashboard/mock_data.py` (Task 6).
- Produces: URL name `"payslip_detail"` → `GET /me/payslips/<int:payslip_id>/`. Reusable `empty_state.html` template (block `content`, context var `message`) for future "nothing here" cases. The next task (Employee Self-Service) links to this URL by name.

- [ ] **Step 1: Write the failing tests**

Append to `dashboard/tests.py`:

```python
class PayslipDetailTests(TestCase):
    def test_requires_login(self):
        response = self.client.get("/me/payslips/1/")
        self.assertEqual(response.status_code, 302)

    def test_shows_itemized_breakdown(self):
        self.client.login(username="amara_okafor", password="buscom-emp-2026")
        response = self.client.get("/me/payslips/1/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/payslip_detail.html")
        self.assertContains(response, "Base Salary")

    def test_missing_payslip_returns_404(self):
        self.client.login(username="amara_okafor", password="buscom-emp-2026")
        response = self.client.get("/me/payslips/999/")
        self.assertEqual(response.status_code, 404)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test dashboard -v 2`
Expected: FAIL — `/me/payslips/1/` route doesn't exist (404 for the wrong reason: no route at all, vs. the intended "not found" 404 which should come from Step 3's view)

- [ ] **Step 3: Implement the view**

Append to `dashboard/views.py`:

```python
from django.http import Http404

from .mock_data import PAYSLIPS


@login_required
def payslip_detail(request, payslip_id):
    payslip = next((p for p in PAYSLIPS if p["id"] == payslip_id), None)
    if payslip is None:
        raise Http404("Payslip not found.")
    return render(request, "dashboard/payslip_detail.html", {"payslip": payslip})
```

- [ ] **Step 4: Wire up the URL**

In `dashboard/urls.py`, add to `urlpatterns`:

```python
    path("me/payslips/<int:payslip_id>/", views.payslip_detail, name="payslip_detail"),
```

- [ ] **Step 5: Write the payslip detail template**

Create `dashboard/templates/dashboard/payslip_detail.html`:

```html
{% extends "dashboard/base.html" %}
{% block title %}Payslip — BusCom{% endblock %}
{% block content %}
<div class="max-w-2xl mx-auto bg-white dark:bg-slate-800 rounded-xl shadow p-8 print:shadow-none print:border-none">
  <div class="flex justify-between items-start mb-6">
    <div>
      <h1 class="text-xl font-semibold">Payslip &mdash; {{ payslip.period }}</h1>
      <p class="text-slate-500 text-sm">BusCom Payroll</p>
    </div>
    <button onclick="window.print()" type="button"
            class="print:hidden rounded-lg border border-slate-300 dark:border-slate-600 px-3 py-1.5 text-sm hover:bg-slate-100 dark:hover:bg-slate-700 transition">
      Print
    </button>
  </div>
  <table class="w-full text-sm mb-6">
    <tbody>
      {% for item in payslip.breakdown %}
      <tr class="border-b border-slate-100 dark:border-slate-700">
        <td class="py-2">{{ item.label }}</td>
        <td class="py-2 text-right {% if item.amount < 0 %}text-red-500{% endif %}">{{ item.amount }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
  <div class="flex justify-between text-base font-semibold border-t border-slate-200 dark:border-slate-700 pt-4">
    <span>Net Pay</span>
    <span>${{ payslip.net }}</span>
  </div>
</div>
{% endblock %}
```

- [ ] **Step 6: Write the reusable empty-state template**

Create `dashboard/templates/dashboard/empty_state.html`:

```html
{% extends "dashboard/base.html" %}
{% block title %}BusCom{% endblock %}
{% block content %}
<div class="flex flex-col items-center justify-center h-full text-center text-slate-500">
  <p>{{ message }}</p>
</div>
{% endblock %}
```

- [ ] **Step 7: Rebuild Tailwind CSS**

```bash
./tailwindcss -i ./dashboard/static/dashboard/css/input.css -o ./dashboard/static/dashboard/css/output.css --minify
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `python manage.py test dashboard -v 2`
Expected: PASS

- [ ] **Step 9: Manually verify in browser**

Run: `python manage.py runserver`, log in as `amara_okafor` / `buscom-emp-2026`, visit `http://127.0.0.1:8000/me/payslips/1/` directly, click "Print", confirm the sidebar/topbar/print button are hidden in the print preview and only the payslip content shows.

- [ ] **Step 10: Commit**

```bash
git add dashboard/views.py dashboard/urls.py dashboard/templates/dashboard/payslip_detail.html dashboard/templates/dashboard/empty_state.html dashboard/tests.py dashboard/static/dashboard/css/output.css
git commit -m "feat: add payslip detail view with print layout and empty-state template"
```

---

### Task 10: Employee Self-Service View

**Files:**
- Modify: `dashboard/views.py`
- Modify: `dashboard/urls.py`
- Create: `dashboard/templates/dashboard/employee_self_service.html`
- Modify: `dashboard/tests.py`

**Interfaces:**
- Consumes: `EMPLOYEES` (imported in Task 7) and `PAYSLIPS` (imported in Task 9) from `dashboard/mock_data.py`; `animateCountUp` from `motion.js` (Task 4); URL name `"payslip_detail"` (Task 9), linked to from this task's template.
- Produces: URL name `"employee_self_service"` → `GET /me/`. View matches the logged-in user by `request.user.email` against `EMPLOYEES[*]["email"]`.

- [ ] **Step 1: Write the failing tests**

Append to `dashboard/tests.py`:

```python
class EmployeeSelfServiceTests(TestCase):
    def test_requires_login(self):
        response = self.client.get("/me/")
        self.assertEqual(response.status_code, 302)

    def test_employee_sees_own_profile_and_payslips(self):
        self.client.login(username="amara_okafor", password="buscom-emp-2026")
        response = self.client.get("/me/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/employee_self_service.html")
        self.assertContains(response, "Senior Backend Engineer")
        self.assertContains(response, "June 2026")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test dashboard -v 2`
Expected: FAIL — `/me/` route doesn't exist (404)

- [ ] **Step 3: Implement the view**

Append to `dashboard/views.py`. No new imports are needed — `EMPLOYEES` and `PAYSLIPS` are already imported from Tasks 7 and 9:

```python
@login_required
def employee_self_service(request):
    employee = next(
        (e for e in EMPLOYEES if e["email"] == request.user.email),
        EMPLOYEES[0],
    )
    payslips = [p for p in PAYSLIPS if p["employee_id"] == employee["id"]]
    return render(request, "dashboard/employee_self_service.html", {
        "employee": employee,
        "payslips": payslips,
    })
```

- [ ] **Step 4: Wire up the URL**

In `dashboard/urls.py`, add to `urlpatterns`:

```python
    path("me/", views.employee_self_service, name="employee_self_service"),
```

- [ ] **Step 5: Write the template**

Create `dashboard/templates/dashboard/employee_self_service.html`:

```html
{% extends "dashboard/base.html" %}
{% block title %}My Profile — BusCom{% endblock %}
{% block content %}
<div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
  <div class="rounded-xl bg-white dark:bg-slate-800 shadow p-6">
    <div class="flex items-center gap-3 mb-4">
      <span class="w-12 h-12 rounded-full bg-indigo-100 dark:bg-indigo-900 text-indigo-600 dark:text-indigo-300 flex items-center justify-center font-medium">
        {{ employee.initials }}
      </span>
      <div>
        <p class="font-semibold">{{ employee.name }}</p>
        <p class="text-sm text-slate-500">{{ employee.designation }}</p>
      </div>
    </div>
    <dl class="text-sm space-y-2">
      <div class="flex justify-between"><dt class="text-slate-500">Department</dt><dd>{{ employee.department }}</dd></div>
      <div class="flex justify-between"><dt class="text-slate-500">Experience</dt><dd>{{ employee.experience_years }} yrs</dd></div>
      <div class="flex justify-between"><dt class="text-slate-500">Email</dt><dd>{{ employee.email }}</dd></div>
    </dl>
  </div>

  <div class="rounded-xl bg-white dark:bg-slate-800 shadow p-6" x-data x-init="animateCountUp($el.querySelector('.stat-value'), {{ employee.salary }}, { prefix: '$' })">
    <p class="text-sm text-slate-500">Current Annual Salary</p>
    <p class="stat-value text-3xl font-semibold mt-1">$0</p>
  </div>
</div>

<div class="rounded-xl bg-white dark:bg-slate-800 shadow p-6">
  <h2 class="font-semibold mb-4">Payslips</h2>
  {% if payslips %}
  <table class="w-full text-sm">
    <thead>
      <tr class="text-left text-slate-500 border-b border-slate-200 dark:border-slate-700">
        <th class="py-2">Period</th>
        <th class="py-2 text-right">Net Pay</th>
        <th class="py-2 text-right">Details</th>
      </tr>
    </thead>
    <tbody>
      {% for payslip in payslips %}
      <tr class="border-b border-slate-100 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700/50 transition">
        <td class="py-2">{{ payslip.period }}</td>
        <td class="py-2 text-right">${{ payslip.net }}</td>
        <td class="py-2 text-right">
          <a href="{% url 'payslip_detail' payslip.id %}" class="text-indigo-600 hover:underline">View</a>
        </td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
  {% else %}
    <p class="text-slate-500 text-sm">No payslips yet.</p>
  {% endif %}
</div>
{% endblock %}
```

- [ ] **Step 6: Rebuild Tailwind CSS**

```bash
./tailwindcss -i ./dashboard/static/dashboard/css/input.css -o ./dashboard/static/dashboard/css/output.css --minify
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `python manage.py test dashboard -v 2`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add dashboard/views.py dashboard/urls.py dashboard/templates/dashboard/employee_self_service.html dashboard/tests.py dashboard/static/dashboard/css/output.css
git commit -m "feat: add employee self-service profile and payslip list"
```

---

### Task 11: Custom 404/500 Error Pages

**Files:**
- Create: `dashboard/templates/404.html`
- Create: `dashboard/templates/500.html`
- Modify: `buscom/settings.py` (verify `DEBUG = False` behavior path — no code change needed if already present, see Step 3)

**Interfaces:**
- Consumes: `dashboard/css/output.css` (Task 3). These templates are standalone (do not extend `base.html`) since Django's `500.html` must render without relying on custom context processors or app-level template inheritance succeeding.
- Produces: styled error pages Django serves automatically when `DEBUG = False` and a request 404s or a view raises an unhandled exception.

- [ ] **Step 1: Write the 404 template**

Create `dashboard/templates/404.html`:

```html
{% load static %}
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Not found — BusCom</title>
  <link rel="stylesheet" href="{% static 'dashboard/css/output.css' %}">
</head>
<body class="min-h-screen flex items-center justify-center bg-slate-50 text-slate-900">
  <div class="text-center">
    <h1 class="text-2xl font-semibold mb-2">Page not found</h1>
    <p class="text-slate-500">The page you're looking for doesn't exist.</p>
    <a href="/" class="mt-4 inline-block text-indigo-600 hover:underline">Go home</a>
  </div>
</body>
</html>
```

- [ ] **Step 2: Write the 500 template**

Create `dashboard/templates/500.html`:

```html
{% load static %}
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Something went wrong — BusCom</title>
  <link rel="stylesheet" href="{% static 'dashboard/css/output.css' %}">
</head>
<body class="min-h-screen flex items-center justify-center bg-slate-50 text-slate-900">
  <div class="text-center">
    <h1 class="text-2xl font-semibold mb-2">Something went wrong</h1>
    <p class="text-slate-500">Please try again in a moment.</p>
    <a href="/" class="mt-4 inline-block text-indigo-600 hover:underline">Go home</a>
  </div>
</body>
</html>
```

- [ ] **Step 3: Verify these templates are reachable by Django's error handling**

Django only renders `404.html`/`500.html` automatically when `DEBUG = False`. Confirm `buscom/settings.py` still has the default `DEBUG = True` for local dev (no change needed) — these templates will take effect automatically in a production-style run. To manually sanity-check the template content itself (not the full DEBUG=False error path), temporarily set `DEBUG = False` and `ALLOWED_HOSTS = ["localhost", "127.0.0.1"]` in a local shell, run `python manage.py runserver`, and visit a nonexistent URL like `/does-not-exist/`.

Expected: styled "Page not found" screen, not Django's default debug traceback.

Revert `DEBUG` back to `True` afterward for continued local development.

- [ ] **Step 4: Commit**

```bash
git add dashboard/templates/404.html dashboard/templates/500.html
git commit -m "feat: add styled 404 and 500 error pages"
```

---

## Post-Implementation Checklist

- [ ] `python manage.py test dashboard -v 2` passes with all tests from Tasks 1, 2, 5, 7, 9, 10 green
- [ ] Manual browser walkthrough: login (both roles) → HR dashboard (search, add employee, count-up, skeleton, stagger, toast) → employee self-service (count-up, payslip list) → payslip detail (breakdown, print) → logout
- [ ] Dark mode toggle works and persists across reload (`localStorage`)
- [ ] No browser console errors on any of the above pages
