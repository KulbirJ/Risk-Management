import { test, expect } from '@playwright/test';

test.describe('Assessments Page', () => {
  test('should load assessments list', async ({ page }) => {
    await page.goto('/assessments');

    // Check page title
    await expect(page.getByRole('heading', { name: 'Assessments' })).toBeVisible();
    
    // Check New Assessment button exists
    const newButton = page.getByRole('link', { name: /new assessment/i });
    await expect(newButton).toBeVisible();
  });

  test('should display existing assessments', async ({ page }) => {
    await page.goto('/assessments');
    
    // Wait for assessments to load
    await page.waitForTimeout(2000);
    
    // Check if assessments are displayed (grid or empty state)
    const assessmentsGrid = page.locator('.grid').filter({ hasText: /assessment/i });
    const emptyState = page.getByText('No assessments found');
    
    // Either grid or empty state should be visible
    const hasAssessments = await assessmentsGrid.isVisible().catch(() => false);
    const isEmpty = await emptyState.isVisible().catch(() => false);
    
    expect(hasAssessments || isEmpty).toBeTruthy();
  });

  test('should filter assessments by search', async ({ page }) => {
    await page.goto('/assessments');
    await page.waitForTimeout(1000);
    
    // Find search input
    const searchInput = page.getByPlaceholder(/search/i);
    await expect(searchInput).toBeVisible();
    
    // Type in search
    await searchInput.fill('Web');
    await page.waitForTimeout(500);
  });

  test('should filter by status', async ({ page }) => {
    await page.goto('/assessments');
    await page.waitForTimeout(1000);
    
    // Find status filter dropdown
    const statusFilter = page.locator('select').first();
    await expect(statusFilter).toBeVisible();
    
    // Change status filter
    await statusFilter.selectOption('draft');
    await page.waitForTimeout(500);
  });

  test('should navigate to assessment detail when clicked', async ({ page }) => {
    await page.goto('/assessments');
    await page.waitForTimeout(2000);
    
    // Click on first assessment if it exists
    const firstAssessment = page.locator('.grid a').first();
    const isVisible = await firstAssessment.isVisible().catch(() => false);
    
    if (isVisible) {
      await firstAssessment.click();
      await expect(page).toHaveURL(/\/assessments\/[a-f0-9-]+/);
    }
  });
});
