# CRM Pro – User Guide

Welcome to CRM Pro. This guide explains how each role uses the system and provides step‑by‑step instructions for every feature available in the app.

- Audience: Sales Reps, Sales Managers, Marketing, Admins, Superadmins
- Apps/Modules: Dashboard, Leads, Communications, Accounts (Profile & User Management)
- UI Conventions: Left sidebar navigation (collapsible), top bar actions, content cards and tables


## Roles and Access

Roles are defined in `accounts.models.CustomUser.ROLE_CHOICES`:
- superadmin
- admin
- sales_manager
- sales_rep
- marketing

High‑level access rules:
- Sales Rep: Own leads and own communications only.
- Sales Manager: Own + team (sales reps in same department) for leads and activities.
- Admin / Superadmin: Full access to leads and user management.
- Marketing: Full access to communications it owns; no user management by default.


## Navigation Basics

- Sidebar: Collapsible, grey themed, sections for Dashboard, Leads, Communications, and Settings.
- Submenus: Click a parent item (e.g., Leads, Communications) to expand child links.
- Active page: Highlighted; parent sections auto‑expand when on a child route.
- Mobile: Use the menu button in the top bar to open/close the sidebar.


## Dashboard

Pages: `Dashboard → Dashboard`, `Dashboard → Analytics`

What you see depends on role (e.g., reps see their own stats; managers/admins see broader data).

- View Overview
  1) Open `Dashboard` from the sidebar.
  2) Use date range options in the page to switch between Today/Week/Month/Quarter/Year.
  3) Review cards for totals, conversion rate, revenue, overdue leads, and recent activities.

- Analytics
  1) Open `Dashboard → Analytics`.
  2) Explore charts for trends, performance, and funnel.

- Export Report (Dashboard)
  1) From Dashboard, locate export/report actions.
  2) Click export to download a CSV/compiled report for the selected period.

Notes
- Data scopes: Reps see own; Managers see self + team; Admin/Superadmin see all.


## Leads

Pages: `Leads → All Leads`, `Leads → Create Lead`, `Leads → Export`

- List and Search
  1) Open `Leads → All Leads`.
  2) Filter by Status, Priority, Source; search by name, email, company, phone.
  3) For managers/admins: filter by Assigned To (sales rep) and date range.
  4) Click a lead row to view details.

- Create a Lead
  1) Open `Leads → Create Lead`.
  2) Fill in contact, company, status/priority, source, and assignment.
  3) Submit. A success message confirms creation; the lead appears in the list.

- View/Update a Lead
  1) From the list or a link, open a lead detail page.
  2) Use Update to modify fields (status, owner, details) if permitted by role.

- Delete a Lead
  1) Open the lead detail.
  2) Select Delete; confirm. A success message confirms deletion.

- Lead Activities
  1) On the lead detail page, use Add Activity to log Calls, Emails, Meetings, Notes.
  2) Contact activities automatically update “Last Contacted”.
  3) View activity history via the Activities tab/link.

- Bulk Update
  1) Open `Leads → All Leads`.
  2) Apply filters or search to narrow results.
  3) Use bulk actions (e.g., status/owner change) as available.

- Export Leads (CSV)
  1) Open `Leads → Export` or use the Export action.
  2) The export respects current filters and your data access scope.

Role scope in Leads (enforced in views)
- Sales Rep: Only leads assigned to the user.
- Sales Manager: User’s own leads + team’s leads (same department).
- Admin/Superadmin: All leads.


## Communications

Pages: `Communications → Email → Campaigns`, `Templates`, `Sequences`, `Settings`, `Analytics`, plus Quick/Bulk Email features.

Ownership model: Most communications resources are owned by the creator; lists filter to the current user’s items. Shared templates are visible when marked shared.

- Email Configuration
  1) Open `Communications → Email → Settings`.
  2) Create a configuration with SMTP/API credentials (per‑user).
  3) Update or Test using the Test action to verify delivery.

- Templates
  1) Open `Communications → Email → Templates`.
  2) Create: set name, subject, and body (with merge fields).
  3) Preview: use Template Preview to render sample data.
  4) Update or share as needed.

- Campaigns
  1) Open `Communications → Email → Campaigns`.
  2) Create: choose template, audience, and sending options (send now or schedule).
  3) Start/Pause: use actions on the campaign detail.
  4) Review stats on the detail page (opens, clicks, etc.).

- Quick Email to a Lead
  1) From a Lead detail page, choose Send Email.
  2) Select a template or write a custom message.
  3) Send. The email is linked to the lead.

- Bulk Email
  1) Open `Communications → Email → Bulk Email`.
  2) Filter/select intended leads; choose template and configuration.
  3) Send. Track status in Emails list or Campaigns.

- Sequences
  1) Open `Communications → Email → Sequences`.
  2) Create a sequence and add steps using “Add Step” (delays, templates).
  3) Assign to a lead list or use in campaigns (where supported).

- Emails List & Detail
  1) Open `Communications → Email → Emails`.
  2) Select an email to view delivery, open, and click events.

- Analytics
  1) Open `Communications → Email → Analytics`.
  2) Review performance across templates and campaigns.

Notes
- Access: All authenticated users can use communications on their own data; admins see additional breadth where implemented by ownership.
- Tracking: Embedded tracking route records opens/clicks for analytics.


## Accounts

Pages: `Settings → Account → Profile`, `Settings → Account → Admin Panel` (role‑gated), Login/Logout, Password Reset.

- Login
  1) Navigate to `/accounts/login/`.
  2) Enter username and password; optionally check Remember Me.
  3) Submit to access the dashboard.

- Logout
  1) Use `Settings → Account → Logout`.

- Password Reset
  1) Go to `Forgot password` on the login page.
  2) Enter your account email to receive a reset link.
  3) Follow the link to set a new password; complete the flow.

- Profile
  1) Open `Settings → Account → Profile`.
  2) Update name, email, phone, department, and profile picture.
  3) Save changes; a success notice confirms updates.

- User Management (Admins/Superadmins only)
  1) Open `User Management` from the sidebar.
  2) Users List: Search and paginate through users.
  3) Create User: Provide username, email, role, department, password.
  4) User Detail/Update: Edit role, department, activation, and contact details.
  5) Toggle Status/Delete: Use actions to deactivate or remove users.
  6) Admin Panel: Open `/admin/` in a new tab for advanced operations.


## Role‑Feature Matrix (Summary)

- Sales Rep
  - Dashboard: own stats, recent activities, recent leads
  - Leads: list/search/filter own; create/update own; add activities; export own scope
  - Communications: configs, templates, campaigns, sequences, emails (own)
  - Accounts: profile, password reset, logout

- Sales Manager
  - Dashboard: own + team metrics, top performers
  - Leads: own + team; create/update; activities; bulk ops; export scoped
  - Communications: same as rep (own items)
  - Accounts: profile; no user management

- Marketing
  - Dashboard: general analytics
  - Communications: full for own items (configs, templates, campaigns, sequences)
  - Leads: read/search may be limited depending on policies; create/update typically not required
  - Accounts: profile

- Admin/Superadmin
  - Dashboard: global metrics
  - Leads: full access
  - Communications: full for own items (and in some cases global reporting)
  - Accounts: full user management; admin site access


## Tips & Troubleshooting

- Sidebar not scrolling: The sidebar is the scroll container with a sticky header. If it overflows, use the mouse wheel/trackpad within the sidebar area.
- Missing menu items: Menus are role‑based. Ensure your account has the expected role. Admin features require `admin` or `superadmin`.
- Email delivery test fails: Verify Email Configuration credentials in `Communications → Email → Settings` and use the Test action.
- Lead not visible: Reps only see assigned leads; managers see team; admins see all.
- CSV exports: Exports respect current filters and your access scope.


## Glossary

- Lead: A potential customer record with status/priority.
- Activity: Logged interaction (call, email, meeting, note) on a lead.
- Template: Reusable email content with merge fields.
- Campaign: Batch email send using a template and recipient set.
- Sequence: Timed series of emails for nurturing.

