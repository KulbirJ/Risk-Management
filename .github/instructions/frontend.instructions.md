---
applyTo: "frontend/**"
---

# Frontend Development Instructions

These instructions apply whenever you are editing files under `frontend/`.

---

## Framework & Directory Layout

- **Next.js 14 App Router** — no `pages/` directory. All pages live under `frontend/app/`.
- **TypeScript 5** — strict mode enabled (`tsconfig.json`).
- **Tailwind CSS** — utility-first styling only. No other CSS frameworks or inline `style={}` props.

```
frontend/
├── app/                    ← Next.js App Router pages
│   ├── page.tsx            ← Dashboard homepage
│   ├── assessments/        ← Assessment list, detail ([id]/), and create (new/)
│   ├── active-risks/       ← Risk register
│   ├── audit-logs/         ← Audit trail viewer
│   └── intelligence/       ← Phase 1 (do not modify)
├── components/             ← Shared reusable components
├── lib/
│   ├── api-client.ts       ← Centralized Axios HTTP client (ALL API calls go here)
│   └── types.ts            ← All TypeScript domain types
└── public/                 ← Static assets
```

---

## API Calls — always use `lib/api-client.ts`

Never call `fetch()` or `axios` directly in pages or components. All HTTP requests must go through the centralized client in `lib/api-client.ts`, which handles the base URL and required auth headers (`X-Tenant-ID`, `X-User-ID`).

```typescript
// CORRECT
import { apiClient } from '@/lib/api-client';

const assessments = await apiClient.get('/api/v1/assessments/');

// WRONG — never do this in a component/page
const res = await fetch('http://localhost:8000/api/v1/assessments/');
```

When adding a new API call, add the function to `lib/api-client.ts` rather than inlining it.

---

## TypeScript Types — always use `lib/types.ts`

All domain types (Assessment, Threat, Evidence, Recommendation, ActiveRisk, AuditLog, User, Tenant) are defined in `lib/types.ts`. Always import and extend these — never redefine domain types inline.

```typescript
// CORRECT
import type { Assessment, Threat } from '@/lib/types';

// WRONG
interface Assessment { id: string; title: string; ... } // inline redefinition
```

---

## Shared Components — reuse before creating

Always check `components/` before building a new component. Existing shared components:

| Component | Purpose |
|---|---|
| `Layout.tsx` | App shell with navigation sidebar — wrap all pages in this |
| `Badge.tsx` | Status/severity colour indicators |
| `Button.tsx` | Themed primary/secondary/danger buttons |
| `Alert.tsx` | Success/error/warning/info notifications |
| `LoadingSpinner.tsx` | Loading state indicator |
| `ThreatModal.tsx` | Threat create/edit modal dialog |
| `ActiveRiskModal.tsx` | Risk acceptance workflow modal |
| `AuthProvider.tsx` | Auth context — provides `useAuth()` hook |

---

## Authentication Context

Use the `useAuth()` hook from `components/AuthProvider.tsx` to access user and tenant context. Never read auth headers directly from storage in components.

```typescript
import { useAuth } from '@/components/AuthProvider';

export default function MyPage() {
  const { user, tenantId } = useAuth();
  // ...
}
```

---

## Styling with Tailwind CSS

- Use only Tailwind utility classes — no external component libraries.
- Follow existing design patterns in the codebase for spacing, colours, and typography.
- Use `className` prop — never `style={}` except for truly dynamic values unavailable in Tailwind.

---

## Page Pattern

New pages should follow this pattern:

```typescript
'use client';

import { useEffect, useState } from 'react';
import Layout from '@/components/Layout';
import LoadingSpinner from '@/components/LoadingSpinner';
import Alert from '@/components/Alert';
import { apiClient } from '@/lib/api-client';
import type { Assessment } from '@/lib/types';

export default function AssessmentsPage() {
  const [data, setData] = useState<Assessment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiClient.get('/api/v1/assessments/')
      .then(res => setData(res.data))
      .catch(() => setError('Failed to load assessments'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Layout><LoadingSpinner /></Layout>;
  if (error) return <Layout><Alert type="error" message={error} /></Layout>;

  return (
    <Layout>
      {/* page content */}
    </Layout>
  );
}
```

---

## Phase 1 Components (do not modify unless working on Phase 1)

These components exist but are **not yet wired to live data**. Leave them as-is for Phase 0 work:

- `IntelEnrichmentPanel.tsx` — threat intelligence display
- `MLScoringPanel.tsx` — ML-based risk scoring
- `KillChainFlow.tsx` — kill chain visualization
- `ThreatGraphPanel.tsx` — threat relationship graph
- `AttackContextPanel.tsx` — MITRE ATT&CK matrix panel

These are Phase 1 features driven by AWS Bedrock + Textract.

---

## Key Conventions

- All pages are `'use client'` components unless you have a specific reason for server components.
- Use `useEffect` + `useState` for data fetching (no React Query or SWR installed).
- Error boundaries are not implemented — show inline `<Alert type="error" />` on failure.
- Use `next/link` for internal navigation, never `<a href>`.
- Use `next/image` for images, never `<img>`.
- Keep all environment-specific values (API base URL, Cognito config) in environment variables accessed via `process.env.NEXT_PUBLIC_*`.
