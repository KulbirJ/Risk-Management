import { test, expect } from '@playwright/test';

test.describe('Active Risks Page', () => {
  test('should load active risks page', async ({ page }) => {
    await page.goto('/active-risks');

    // Check page title (actual title is 'Risk Register')
    await expect(page.getByRole('heading', { name: /risk register/i })).toBeVisible();
  });

  test('should have filter controls', async ({ page }) => {
    await page.goto('/active-risks');
    await page.waitForTimeout(1000);
    
    // Check for search and filter elements
    const searchInput = page.getByPlaceholder(/search/i);
    const statusFilter = page.locator('select').first();

    await expect(searchInput).toBeVisible();
    await expect(statusFilter).toBeVisible();
  });

  test('should display risks or empty state', async ({ page }) => {
    await page.goto('/active-risks');
    await page.waitForTimeout(2000);
    
    // Either risks grid or empty state should be visible
    const risksGrid = page.locator('.grid').filter({ hasText: /risk/i });
    const emptyState = page.getByText(/no.*risks/i);
    
    const hasRisks = await risksGrid.isVisible().catch(() => false);
    const isEmpty = await emptyState.isVisible().catch(() => false);
    
    expect(hasRisks || isEmpty).toBeTruthy();
  });
});
