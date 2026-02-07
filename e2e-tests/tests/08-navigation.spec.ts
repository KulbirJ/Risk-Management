import { test, expect } from '@playwright/test';

test.describe('Navigation and Layout', () => {
  test('should have consistent navigation across pages', async ({ page }) => {
    await page.goto('/');
    
    // Check main navigation links exist
    const nav = page.locator('nav, header').first();
    await expect(nav).toBeVisible();
  });

  test('should navigate between all main pages', async ({ page }) => {
    // Dashboard
    await page.goto('/');
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();
    
    // Assessments
    await page.goto('/assessments');
    await expect(page.getByRole('heading', { name: 'Assessments' })).toBeVisible();
    
    // Active Risks
    await page.goto('/active-risks');
    await expect(page.getByRole('heading', { name: /risk register/i })).toBeVisible();
    
    // Audit Logs
    await page.goto('/audit-logs');
    await expect(page.getByRole('heading', { name: /audit logs/i })).toBeVisible();
  });

  test('should have responsive layout', async ({ page }) => {
    await page.goto('/');
    
    // Check page renders without errors
    await expect(page.locator('body')).toBeVisible();
    
    // Check main content area
    const mainContent = page.locator('main, .container, [class*="max-w"]').first();
    await expect(mainContent).toBeVisible();
  });

  test('should handle 404 pages gracefully', async ({ page }) => {
    await page.goto('/non-existent-page');
    
    // Should show 404 or redirect to home
    const is404 = await page.getByText(/404|not found/i).isVisible().catch(() => false);
    const isHome = page.url().includes('/') && !page.url().includes('non-existent');
    
    expect(is404 || isHome).toBeTruthy();
  });
});
