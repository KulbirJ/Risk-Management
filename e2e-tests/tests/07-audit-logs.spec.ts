import { test, expect } from '@playwright/test';

test.describe('Audit Logs Page', () => {
  test('should load audit logs page', async ({ page }) => {
    await page.goto('/audit-logs');

    // Check page title
    await expect(page.getByRole('heading', { name: /audit logs/i })).toBeVisible();
  });

  test('should have filter controls', async ({ page }) => {
    await page.goto('/audit-logs');
    await page.waitForTimeout(1000);
    
    // Check for search/filter elements
    const filterElement = page.locator('input, select').first();
    await expect(filterElement).toBeVisible();
  });

  test('should display audit logs or empty state', async ({ page }) => {
    await page.goto('/audit-logs');
    await page.waitForTimeout(2000);
    
    // Either logs table or empty state should be visible
    const logsTable = page.locator('table, .space-y-4');
    const emptyState = page.getByText(/no.*logs|no activities/i);
    
    const hasLogs = await logsTable.isVisible().catch(() => false);
    const isEmpty = await emptyState.isVisible().catch(() => false);
    
    expect(hasLogs || isEmpty).toBeTruthy();
  });
});
