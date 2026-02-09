import { test, expect } from '@playwright/test';

test.describe('Dashboard Page', () => {
  test('should load dashboard successfully', async ({ page }) => {
    await page.goto('/');
    
    // Check page title
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();
    await expect(page.getByText('Active Risks')).toBeVisible();
    await expect(page.getByText('Critical Threats')).toBeVisible();
  });

  test('should display stats with numbers', async ({ page }) => {
    await page.goto('/');
    
    // Wait for data to load
    await page.waitForTimeout(2000);
    
    // Check that stats are displayed
    const statsSection = page.locator('.grid').first();
    await expect(statsSection).toBeVisible();
  });

  test('should have New Assessment button', async ({ page }) => {
    await page.goto('/');
    
    const newAssessmentButton = page.getByRole('link', { name: /new assessment/i });
    await expect(newAssessmentButton).toBeVisible();
  });

  test('should navigate to assessments page', async ({ page }) => {
    await page.goto('/');
    
    await page.getByText('View all assessments').click();
    await expect(page).toHaveURL('/assessments');
  });
});
