# BusCom Frontend Design

Date: 2026-08-09

## Purpose

BusCom is a SaaS web application for companies to manage employee salaries
(based on experience and other factors, defined later) with two user roles:

- **HR/admin** — manages employee records and salary/payroll data
- **Employee** — self-service view of their own profile, salary, and payslips

This spec covers the **frontend of the application itself** (not a marketing
site). Business logic for salary calculation is explicitly deferred; this
phase focuses on screens, layout, and UI/UX motion design, backed by mocked
data.

## Stack

- **Backend framework:** Django (chosen for built-in auth, admin, and ORM —
  a natural fit for a multi-role HR app)
- **Templates:** Django template engine, server-rendered
- **Styling:** Tailwind CSS via the standalone CLI binary (no Node/npm
  dependency — keeps the project Python-first)
- **Interactivity:** Alpine.js for lightweight client-side state (toggles,
  dropdowns, modals)
- **Motion:** GSAP for animations (transitions, staggered lists, count-ups,
  skeleton loaders)
- **Database:** SQLite (dev), used only for Django auth at this stage
- **Auth:** Django's built-in `User` model, extended with a `role` field
  (`hr` / `employee`) to branch navigation, permissions, and views

## Architecture

Single Django project `buscom` with one app, `dashboard`, holding all pages
for this phase (login, HR views, employee self-service views). No
multi-app split yet — the app is small enough that one app stays clear;
this can be revisited if it grows.

All pages extend a shared `base.html` providing the app shell: role-aware
sidebar navigation, topbar with user menu, and a light/dark theme toggle.

Employee, salary, and payslip data are **mocked** as plain Python
dicts/lists passed into template context. The shape of this mock data
mirrors what real ORM models will eventually look like, so that wiring up
actual business logic later is a data-layer swap, not a template rewrite.

## Screens

1. **Login** — Django auth login form, styled to match the app shell
2. **HR Dashboard**
   - Stat cards: headcount, total payroll, average salary (animated
     count-up on load)
   - Employee directory: searchable/filterable table
   - Add/edit employee modal
3. **Employee self-service view**
   - Profile card (name, role, experience, etc.)
   - Salary summary card
   - Payslip list
4. **Payslip detail** — itemized breakdown, print-ready layout
5. **Shared shell** — role-aware sidebar (HR sees admin links, employee
   sees a reduced set), topbar, theme toggle

## Motion & UX patterns

Motion is used to clarify state changes, not as decoration. Kept
restrained and consistent across screens:

- Page/section entrance transitions (fade + slide) on load
- Staggered row entrance for tables and lists
- Animated count-up for currency/stat figures
- Skeleton loading placeholders before content settles in
- Hover/press micro-interactions on buttons, table rows, and cards
- Modal/dialog enter-exit animation (scale + fade)
- Toast notifications (slide-in) for actions, e.g. "Employee added"
- Inline form-error feedback (shake/highlight) on validation failure

Implemented via GSAP timelines, with Alpine.js managing the underlying
UI state (open/closed, active tab, etc.) that GSAP animates against.

## Data flow

Views construct mock data (Python dicts/lists matching the eventual model
shape) and pass it into template context. No real persistence for
employee/salary/payslip data yet — only Django's `User`/auth tables are
real, backed by SQLite.

## Error handling

Minimal, appropriate for this stage:

- Inline validation feedback on forms (e.g. add/edit employee)
- Empty-state screens where data is absent (e.g. "No payslips yet")
- Standard Django 404/500 error pages, restyled to match the app shell

## Testing

- Django smoke tests: each page route returns HTTP 200 and renders the
  expected template
- Motion/visual correctness is verified manually in-browser during
  implementation — not covered by automated tests, since it's a visual
  concern

## Out of scope (this phase)

- Real salary calculation logic (experience-based rules, performance
  adjustments, etc.)
- Real payroll/payslip persistence and PDF export
- Attendance/leave tracking
- Marketing/landing page
- Multi-tenant support
