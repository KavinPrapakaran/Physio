# Project Plan

**Status**: Approved
**Created**: 2026-10-05
**Mode**: NEW

---

## 1. Project Overview

**Goal**: Build a clinic operations platform for secure patient management, scheduling, assessments, plans, billing, and document-heavy workflows. The project is designed so that every module is independently testable.

**App Type**: SPA + API

**API Login**: Yes

**Mode**: NEW

**Deployment Plan**: No deployment plan found

---

## 2. Backend — API Service

| Component | Technology |
|-----------|-----------|
| **Language** | C# |
| **Runtime** | .NET |
| **Package Manager** | dotnet (NuGet) |
| **Test Runner** | xUnit |
| **Mocking Library** | NSubstitute |
| **Test Command** | dotnet test |
| **Orchestration** | docker-compose |

---

## 3. Frontend — Web App

| Component | Technology |
|-----------|-----------|
| **Language** | TypeScript |
| **Framework** | React + Vite |
| **Package Manager** | npm |
| **Test Runner** | vitest |
| **Mocking Library** | vi.mock |
| **Test Command** | npm test |

---

## 4. Services Required

| Azure Service | Role in App | Environment Variable | Default Value (Local) | Classification |
|---------------|------------|---------------------|----------------------|----------------|
| Blob Storage | Store patient PDFs, generated reports, and uploaded clinical documents | STORAGE_CONNECTION_STRING | UseDevelopmentStorage=true | Essential |
| PostgreSQL | Primary data store for patients, appointments, assessments, treatment plans, invoices, and audit records | DATABASE_URL | postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost:5432/clinicdb | Essential |

---

## 5. Prerequisites

### Run

| Tool | Service(s) | Installed | Version |
|------|------------|-----------|---------|
| Node.js | frontend | ❓ | TBD |
| npm | frontend | ❓ | TBD |
| .NET SDK | backend | ❓ | TBD |
| Docker | backend, frontend | ❓ | TBD |
| Docker Compose | backend, frontend | ❓ | TBD |

### Debug

| Tool | Service(s) | Installed | Version |
|------|------------|-----------|---------|
| ms-dotnettools.csdevkit | backend | ❓ | N/A |
| ms-vscode.vscode-typescript-next | frontend | ❓ | N/A |
| ms-azuretools.vscode-docker | backend, frontend | ❓ | N/A |

---

## 6. Design System & UI

**Component Library**: Fluent UI v9
**Style Direction**: Modern clinical operations console with structured workflows, subtle depth, crisp tables, and clear high-priority actions. The interface emphasizes calm trust, fast triage, and confident task completion without visual clutter.
**Typography**: Inter, system-ui

### Color Palette

| Token | Hex | Usage |
|-------|-----|-------|
| `primary` | `#1F5AA6` | Primary actions, navigation highlights, and key patient workflow states |
| `accent`  | `#1FA0A8` | Secondary emphasis for wellness markers, reminder badges, and summary highlights |
| `surface` | `#F4F7FB` | Main page and panel backgrounds for an airy clinical workspace |
| `text`    | `#18212F` | Core body text for patient details, schedule entries, and form fields |
| `muted`   | `#64748B` | Secondary labels, metadata, timestamps, and subdued status text |
| `border`  | `#D9E2EC` | Dividers, input outlines, and card boundaries |

### Pages

| Page | Route | Purpose | Layout |
|------|-------|---------|--------|
| Dashboard | `/` | Daily operational pulse: agenda, queue, alerts, and pending tasks | `header + nav + grid` |
| Patients | `/patients` | Search and review patient records | `sidebar + table` |
| Patient Detail | `/patients/:id` | Review patient history, notes, and care actions | `two-column(media+meta) + action-bar` |
| Appointments | `/appointments` | Manage the schedule and reminder flow | `header + table` |
| Billing | `/billing` | Review invoices, payment status, and outstanding balances | `header + table` |
| Reports | `/reports` | Exposure to summaries, exports, and compliance activity | `header + card-list` |

### Sample Content

```
Dashboard — patient queue:
| Patient | Next Visit | Provider | Status |
| Alicia Nguyen | 09:30 AM | Dr. Singh | Confirmed |
| Marcus Diaz | 10:15 AM | Dr. Patel | Checked In |
| Leila Hassan | 11:45 AM | Dr. Brooks | Follow Up |
| Olivia Grant | 01:20 PM | Dr. Lee | Pending |

Patients — patient record:
| Name | DOB | Last Visit | Status |
| Alicia Nguyen | 1992-04-17 | 2026-10-05 | Active |
| Marcus Diaz | 1978-11-29 | 2026-10-03 | Active |
| Leila Hassan | 1986-02-12 | 2026-09-28 | Needs Review |
| Olivia Grant | 1995-07-08 | 2026-09-30 | Active |

Appointments — schedule:
| Date | Time | Patient | Type | Status |
| 2026-10-05 | 09:30 | Alicia Nguyen | Consultation | Confirmed |
| 2026-10-05 | 10:15 | Marcus Diaz | Assessment | Checked In |
| 2026-10-05 | 11:45 | Leila Hassan | Follow Up | Scheduled |
| 2026-10-05 | 13:00 | Olivia Grant | Treatment Plan | Pending |

Patient Detail — treatment plan: Treatment plan review with medication summary and reminders
Billing — invoice: INV-2048 · $1,240.00 · Awaiting payment
Reports — export: Monthly clinical summary PDF · Generated yesterday
```

---

## 7. Project Structure

```
clinic-ops/
├─ backend/
│  ├─ src/
│  ├─ tests/
│  ├─ appsettings.Development.json
│  ├─ Program.cs
│  └─ ClinicOps.Api.csproj
├─ frontend/
│  ├─ src/
│  ├─ public/
│  ├─ package.json
│  ├─ vite.config.ts
│  └─ tsconfig.json
├─ docker/
│  ├─ docker-compose.yml
│  └─ .env.example
├─ docs/
│  └─ api-spec.md
├─ .azure/
│  ├─ requirements.json
│  ├─ project-plan.md
│  └─ .preview-temp/
├─ .gitignore
├─ README.md
└─ .env.example
```

---

## 8. Route Definitions

| # | Method | Path | Description | Request Body | Response Body | Status Codes |
|---|--------|------|-------------|-------------|--------------|-------------|
| 1 | GET | `/api/health` | Health check | — | `{ status, services }` | 200, 503 |
| 2 | GET | `/api/patients` | List patients with filters and paging | — | `{ items, page, total }` | 200 |
| 3 | GET | `/api/patients/:id` | Fetch a single patient record | — | `{ patient, documents, reminders }` | 200, 404 |
| 4 | POST | `/api/appointments` | Create or update a schedule entry | `{ patientId, time, clinicianId, type }` | `{ appointment }` | 201, 400 |
| 5 | GET | `/api/reports` | Retrieve generated summaries and exports | — | `{ reports }` | 200 |
| 6 | POST | `/api/invoices` | Create or finalize an invoice | `{ patientId, amount, status }` | `{ invoice }` | 201, 400 |

---

## 9. Next Steps

1. Run **azure-project-scaffold** to execute this plan
2. Run **azure-project-integrate** to wire the frontend to live data, smoke-test the backend, and create the migrations
3. Run **azure-debug-plan** → **azure-debug-generate** for Docker emulators and VS Code debugging
4. Run the **azure-deploy** agent when ready; it uses **azure-app-onboard** for architecture, cost estimation, IaC generation, provisioning, and health verification
