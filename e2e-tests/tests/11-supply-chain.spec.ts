import { test, expect } from '@playwright/test';

test.describe('Supply Chain Risk Assessment', () => {
  // ─── Navigation ────────────────────────────────────────────────────

  test('should show Supply Chain in sidebar navigation', async ({ page }) => {
    await page.goto('/');
    const navLink = page.getByRole('link', { name: /supply chain/i });
    await expect(navLink).toBeVisible();
  });

  test('should navigate to supply chain list page', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('link', { name: /supply chain/i }).click();
    await expect(page).toHaveURL('/supply-chain');
    await expect(page.getByRole('heading', { name: /supply chain risk/i })).toBeVisible();
  });

  // ─── List Page ─────────────────────────────────────────────────────

  test('should display summary stat cards on list page', async ({ page }) => {
    await page.goto('/supply-chain');
    await expect(page.getByText('Assessments')).toBeVisible();
    await expect(page.getByText('Vendors')).toBeVisible();
    await expect(page.getByText('Dependencies')).toBeVisible();
    await expect(page.getByText(/critical.*high.*deps/i)).toBeVisible();
  });

  test('should have a New Assessment button', async ({ page }) => {
    await page.goto('/supply-chain');
    const newBtn = page.getByRole('link', { name: /new assessment/i });
    await expect(newBtn).toBeVisible();
  });

  test('should display empty state when no assessments exist', async ({ page }) => {
    // Intercept and return empty array
    await page.route('**/api/v1/supply-chain/*', route => {
      if (route.request().method() === 'GET') {
        route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
      } else {
        route.continue();
      }
    });
    await page.goto('/supply-chain');
    await page.waitForTimeout(1000);
    await expect(page.getByText(/no supply chain assessments/i)).toBeVisible();
  });

  test('should handle API errors on list page gracefully', async ({ page }) => {
    await page.route('**/api/v1/supply-chain/*', route => route.abort());
    await page.goto('/supply-chain');
    await page.waitForTimeout(2000);
    // Page should render without crashing
    await expect(page.locator('body')).toBeVisible();
  });

  // ─── New Assessment (3-step wizard) ────────────────────────────────

  test('should navigate to new assessment wizard', async ({ page }) => {
    await page.goto('/supply-chain');
    await page.getByRole('link', { name: /new assessment/i }).click();
    await expect(page).toHaveURL('/supply-chain/new');
    await expect(page.getByRole('heading', { name: /new supply chain assessment/i })).toBeVisible();
  });

  test('should display 3-step indicator', async ({ page }) => {
    await page.goto('/supply-chain/new');
    await expect(page.getByText('Basics')).toBeVisible();
    await expect(page.getByText(/technology sensitivity/i)).toBeVisible();
    await expect(page.getByText(/deployment risk/i)).toBeVisible();
  });

  test('should show Step 1 (Basics) fields by default', async ({ page }) => {
    await page.goto('/supply-chain/new');
    await expect(page.getByText('Title *')).toBeVisible();
    await expect(page.getByText('Description')).toBeVisible();
    await expect(page.getByText('Scope')).toBeVisible();
    await expect(page.getByText('Industry Sector')).toBeVisible();
  });

  test('should prevent proceeding without a title', async ({ page }) => {
    await page.goto('/supply-chain/new');
    const nextBtn = page.getByRole('button', { name: /next/i });
    await expect(nextBtn).toBeDisabled();
  });

  test('should advance through wizard steps', async ({ page }) => {
    await page.goto('/supply-chain/new');

    // Step 1: fill title
    await page.getByPlaceholder(/log4j supply chain/i).fill('E2E Test SC Assessment');
    await page.getByRole('button', { name: /next/i }).click();

    // Step 2: Technology Sensitivity — check CCCS description visible
    await expect(page.getByText(/cccs step 1/i)).toBeVisible();
    await expect(page.getByText('Technology Sensitivity')).toBeVisible();
    // Select High
    await page.getByRole('button', { name: 'High' }).first().click();
    await page.getByRole('button', { name: /next/i }).click();

    // Step 3: Deployment Risk
    await expect(page.getByText(/cccs step 3/i)).toBeVisible();
    await expect(page.getByText('Cyber Defence Capability')).toBeVisible();
    await expect(page.getByRole('button', { name: /create assessment/i })).toBeVisible();
  });

  test('should navigate backwards through wizard', async ({ page }) => {
    await page.goto('/supply-chain/new');
    await page.getByPlaceholder(/log4j supply chain/i).fill('Nav Test');
    await page.getByRole('button', { name: /next/i }).click();
    // Now on Step 2 — go back
    await page.getByRole('button', { name: /previous/i }).click();
    // Should be back on Basics, title preserved
    const titleInput = page.getByPlaceholder(/log4j supply chain/i);
    await expect(titleInput).toHaveValue('Nav Test');
  });

  test('should create a new supply chain assessment end-to-end', async ({ page }) => {
    await page.goto('/supply-chain/new');
    const ts = Date.now();

    // Step 1
    await page.getByPlaceholder(/log4j supply chain/i).fill(`SC E2E Test ${ts}`);
    await page.getByPlaceholder(/purpose and objectives/i).fill('Automated e2e test');
    await page.getByRole('button', { name: /next/i }).click();

    // Step 2 — Technology Sensitivity
    await page.getByRole('button', { name: 'High' }).first().click();
    await page.getByRole('button', { name: /next/i }).click();

    // Step 3 — Deployment Risk
    await page.getByRole('button', { name: 'Medium' }).first().click();
    await page.getByRole('button', { name: /create assessment/i }).click();

    // Should redirect to detail page
    await expect(page).toHaveURL(/\/supply-chain\/[a-f0-9-]+/, { timeout: 10000 });
    await expect(page.getByText(`SC E2E Test ${ts}`)).toBeVisible();
  });

  test('should have Back to Supply Chain link on new page', async ({ page }) => {
    await page.goto('/supply-chain/new');
    const backBtn = page.getByRole('button', { name: /back to supply chain/i });
    await expect(backBtn).toBeVisible();
    await backBtn.click();
    await expect(page).toHaveURL('/supply-chain');
  });

  // ─── Detail Page — Overview Tab ────────────────────────────────────

  test('should show detail page tabs', async ({ page }) => {
    // Create a quick assessment via API, then navigate
    const resp = await page.request.post('http://localhost:8000/api/v1/supply-chain/', {
      headers: {
        'X-Tenant-ID': '67636bd3-9846-4bde-806f-aea369fc9457',
        'X-User-ID': '0bc9d6a9-f342-452e-9297-ee33f44d4f84',
        'Content-Type': 'application/json',
      },
      data: { title: 'Detail Tab Test' },
    });
    const body = await resp.json();
    const id = body.id;

    await page.goto(`/supply-chain/${id}`);
    await expect(page.getByText('Overview')).toBeVisible();
    await expect(page.getByText(/vendors/i)).toBeVisible();
    await expect(page.getByText(/dependencies/i)).toBeVisible();
    await expect(page.getByText(/sbom upload/i)).toBeVisible();
  });

  test('should display Recalculate Risk button on detail page', async ({ page }) => {
    const resp = await page.request.post('http://localhost:8000/api/v1/supply-chain/', {
      headers: {
        'X-Tenant-ID': '67636bd3-9846-4bde-806f-aea369fc9457',
        'X-User-ID': '0bc9d6a9-f342-452e-9297-ee33f44d4f84',
        'Content-Type': 'application/json',
      },
      data: { title: 'Score Button Test' },
    });
    const body = await resp.json();
    await page.goto(`/supply-chain/${body.id}`);
    await expect(page.getByRole('button', { name: /recalculate risk/i })).toBeVisible();
  });

  // ─── Detail Page — Vendors Tab (CCCS Step 2) ──────────────────────

  test('should add a vendor via the form', async ({ page }) => {
    const resp = await page.request.post('http://localhost:8000/api/v1/supply-chain/', {
      headers: {
        'X-Tenant-ID': '67636bd3-9846-4bde-806f-aea369fc9457',
        'X-User-ID': '0bc9d6a9-f342-452e-9297-ee33f44d4f84',
        'Content-Type': 'application/json',
      },
      data: { title: 'Vendor Test Assessment' },
    });
    const body = await resp.json();
    await page.goto(`/supply-chain/${body.id}`);

    // Switch to Vendors tab
    await page.getByRole('button', { name: /vendors/i }).click();
    await expect(page.getByText(/step 2.*supplier confidence/i)).toBeVisible();

    // Open vendor form
    await page.getByRole('button', { name: /add vendor/i }).click();

    // Fill vendor fields
    await page.getByLabel(/vendor name/i).fill('Acme Corp');
    await page.getByLabel(/country/i).fill('Canada');

    // Set FOCI risk to Medium
    const fociSection = page.locator('text=FOCI Risk').locator('..');
    await fociSection.getByRole('button', { name: 'Medium' }).click();

    // Save
    await page.getByRole('button', { name: /save vendor/i }).click();

    // Vendor should appear in the list
    await expect(page.getByText('Acme Corp')).toBeVisible();
    // Should show computed confidence
    await expect(page.getByText(/confidence/i)).toBeVisible();
  });

  test('should delete a vendor', async ({ page }) => {
    // Create assessment + vendor via API
    const resp = await page.request.post('http://localhost:8000/api/v1/supply-chain/', {
      headers: {
        'X-Tenant-ID': '67636bd3-9846-4bde-806f-aea369fc9457',
        'X-User-ID': '0bc9d6a9-f342-452e-9297-ee33f44d4f84',
        'Content-Type': 'application/json',
      },
      data: { title: 'Delete Vendor Test' },
    });
    const assess = await resp.json();

    await page.request.post(`http://localhost:8000/api/v1/supply-chain/${assess.id}/vendors`, {
      headers: {
        'X-Tenant-ID': '67636bd3-9846-4bde-806f-aea369fc9457',
        'X-User-ID': '0bc9d6a9-f342-452e-9297-ee33f44d4f84',
        'Content-Type': 'application/json',
      },
      data: { assessment_id: assess.id, name: 'VendorToDelete' },
    });

    await page.goto(`/supply-chain/${assess.id}`);
    await page.getByRole('button', { name: /vendors/i }).click();
    await expect(page.getByText('VendorToDelete')).toBeVisible();

    // Click delete
    await page.getByTitle(/delete vendor/i).click();
    await page.waitForTimeout(500);
    await expect(page.getByText('VendorToDelete')).not.toBeVisible();
  });

  // ─── Detail Page — Dependencies Tab ────────────────────────────────

  test('should add a dependency manually', async ({ page }) => {
    const resp = await page.request.post('http://localhost:8000/api/v1/supply-chain/', {
      headers: {
        'X-Tenant-ID': '67636bd3-9846-4bde-806f-aea369fc9457',
        'X-User-ID': '0bc9d6a9-f342-452e-9297-ee33f44d4f84',
        'Content-Type': 'application/json',
      },
      data: { title: 'Dep Test Assessment' },
    });
    const body = await resp.json();
    await page.goto(`/supply-chain/${body.id}`);

    // Switch to Dependencies tab
    await page.getByRole('button', { name: /dependencies/i }).click();

    // Open add form
    await page.getByRole('button', { name: /^add$/i }).click();

    // Fill in dependency
    await page.getByLabel(/package name/i).fill('log4j-core');
    await page.getByLabel(/version/i).fill('2.14.1');
    await page.getByLabel(/cve ids/i).fill('CVE-2021-44228, CVE-2021-45046');

    await page.getByRole('button', { name: /^save$/i }).click();

    // Should appear in the table
    await expect(page.getByText('log4j-core')).toBeVisible();
    await expect(page.getByText('2.14.1')).toBeVisible();
    await expect(page.getByText('CVE-2021-44228')).toBeVisible();
  });

  test('should show risk level badges for dependencies with CVEs', async ({ page }) => {
    const resp = await page.request.post('http://localhost:8000/api/v1/supply-chain/', {
      headers: {
        'X-Tenant-ID': '67636bd3-9846-4bde-806f-aea369fc9457',
        'X-User-ID': '0bc9d6a9-f342-452e-9297-ee33f44d4f84',
        'Content-Type': 'application/json',
      },
      data: { title: 'Risk Badge Test' },
    });
    const assess = await resp.json();

    // Create a dep with a CVE
    await page.request.post(`http://localhost:8000/api/v1/supply-chain/${assess.id}/dependencies`, {
      headers: {
        'X-Tenant-ID': '67636bd3-9846-4bde-806f-aea369fc9457',
        'X-User-ID': '0bc9d6a9-f342-452e-9297-ee33f44d4f84',
        'Content-Type': 'application/json',
      },
      data: {
        assessment_id: assess.id,
        name: 'spring-core',
        version: '5.3.0',
        cve_ids: ['CVE-2022-22965'],
        cvss_score: 9.8,
      },
    });

    await page.goto(`/supply-chain/${assess.id}`);
    await page.getByRole('button', { name: /dependencies/i }).click();

    await expect(page.getByText('spring-core')).toBeVisible();
    // Should have a risk level badge
    const riskBadge = page.locator('.rounded-full').filter({ hasText: /low|medium|high|critical/i });
    await expect(riskBadge.first()).toBeVisible();
  });

  test('should show ML Enrich button on dependencies tab', async ({ page }) => {
    const resp = await page.request.post('http://localhost:8000/api/v1/supply-chain/', {
      headers: {
        'X-Tenant-ID': '67636bd3-9846-4bde-806f-aea369fc9457',
        'X-User-ID': '0bc9d6a9-f342-452e-9297-ee33f44d4f84',
        'Content-Type': 'application/json',
      },
      data: { title: 'ML Enrich Button Test' },
    });
    const body = await resp.json();
    await page.goto(`/supply-chain/${body.id}`);
    await page.getByRole('button', { name: /dependencies/i }).click();
    await expect(page.getByRole('button', { name: /ml enrich/i })).toBeVisible();
  });

  // ─── Detail Page — SBOM Upload Tab ─────────────────────────────────

  test('should display SBOM upload interface', async ({ page }) => {
    const resp = await page.request.post('http://localhost:8000/api/v1/supply-chain/', {
      headers: {
        'X-Tenant-ID': '67636bd3-9846-4bde-806f-aea369fc9457',
        'X-User-ID': '0bc9d6a9-f342-452e-9297-ee33f44d4f84',
        'Content-Type': 'application/json',
      },
      data: { title: 'SBOM Tab Test' },
    });
    const body = await resp.json();
    await page.goto(`/supply-chain/${body.id}`);
    await page.getByRole('button', { name: /sbom upload/i }).click();
    await expect(page.getByText(/upload a cyclonedx or spdx/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /choose json file/i })).toBeVisible();
  });

  // ─── Risk Scoring ──────────────────────────────────────────────────

  test('should recalculate risk score and show result', async ({ page }) => {
    // Create assessment + vendor via API
    const resp = await page.request.post('http://localhost:8000/api/v1/supply-chain/', {
      headers: {
        'X-Tenant-ID': '67636bd3-9846-4bde-806f-aea369fc9457',
        'X-User-ID': '0bc9d6a9-f342-452e-9297-ee33f44d4f84',
        'Content-Type': 'application/json',
      },
      data: {
        title: 'Scoring Test',
        technology_sensitivity: 'High',
        cyber_defense_level: 'Low',
      },
    });
    const assess = await resp.json();

    // Add a vendor with high risk factors
    await page.request.post(`http://localhost:8000/api/v1/supply-chain/${assess.id}/vendors`, {
      headers: {
        'X-Tenant-ID': '67636bd3-9846-4bde-806f-aea369fc9457',
        'X-User-ID': '0bc9d6a9-f342-452e-9297-ee33f44d4f84',
        'Content-Type': 'application/json',
      },
      data: {
        assessment_id: assess.id,
        name: 'Risky Vendor',
        foci_risk: 'High',
        geopolitical_risk: 'High',
        business_practices_risk: 'High',
        data_protection_maturity: 'Low',
        vuln_mgmt_maturity: 'Low',
        security_policies_maturity: 'Low',
      },
    });

    await page.goto(`/supply-chain/${assess.id}`);

    // Click recalculate
    await page.getByRole('button', { name: /recalculate risk/i }).click();
    await page.waitForTimeout(3000);

    // Score result panel should appear
    await expect(page.getByText(/risk score/i)).toBeVisible();
    await expect(page.getByText(/\/100/)).toBeVisible();
  });

  // ─── Full Journey ──────────────────────────────────────────────────

  test('complete supply chain assessment journey', async ({ page }) => {
    const ts = Date.now();

    // 1. Navigate to supply chain
    await page.goto('/supply-chain');
    await page.getByRole('link', { name: /new assessment/i }).click();

    // 2. Wizard Step 1 — Basics
    await page.getByPlaceholder(/log4j supply chain/i).fill(`Journey SC ${ts}`);
    await page.getByPlaceholder(/purpose and objectives/i).fill('Full journey test');
    await page.getByRole('button', { name: /next/i }).click();

    // 3. Wizard Step 2 — Technology Sensitivity = High
    await page.getByRole('button', { name: 'High' }).first().click();
    await page.getByRole('button', { name: /next/i }).click();

    // 4. Wizard Step 3 — Cyber Defence = Medium → create
    await page.getByRole('button', { name: 'Medium' }).first().click();
    await page.getByRole('button', { name: /create assessment/i }).click();
    await page.waitForURL(/\/supply-chain\/[a-f0-9-]+/, { timeout: 10000 });

    // 5. Verify on detail page
    await expect(page.getByText(`Journey SC ${ts}`)).toBeVisible();

    // 6. Add a vendor
    await page.getByRole('button', { name: /vendors/i }).click();
    await page.getByRole('button', { name: /add vendor/i }).click();
    await page.getByLabel(/vendor name/i).fill('Journey Vendor');
    await page.getByLabel(/country/i).fill('Canada');
    await page.getByRole('button', { name: /save vendor/i }).click();
    await expect(page.getByText('Journey Vendor')).toBeVisible();

    // 7. Add a dependency
    await page.getByRole('button', { name: /dependencies/i }).click();
    await page.getByRole('button', { name: /^add$/i }).click();
    await page.getByLabel(/package name/i).fill('express');
    await page.getByLabel(/version/i).fill('4.17.1');
    await page.getByLabel(/cve ids/i).fill('CVE-2024-12345');
    await page.getByRole('button', { name: /^save$/i }).click();
    await expect(page.getByText('express')).toBeVisible();

    // 8. Recalculate risk
    await page.getByRole('button', { name: /recalculate risk/i }).click();
    await page.waitForTimeout(3000);
    await expect(page.getByText(/\/100/)).toBeVisible();

    // 9. Navigate back to list
    await page.getByRole('button', { name: /back/i }).click();
    await expect(page).toHaveURL('/supply-chain');
    await expect(page.getByText(`Journey SC ${ts}`)).toBeVisible();

    console.log('✅ Complete supply chain journey test passed!');
  });
});
