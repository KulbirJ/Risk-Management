import { test, expect } from '@playwright/test';

let assessmentId: string;

test.describe('Assessment Detail Page', () => {
  test.beforeAll(async ({ browser }) => {
    // Create an assessment to test with
    const page = await browser.newPage();
    await page.goto('/assessments/new');
    
    await page.getByLabel(/assessment title/i).fill('Detail Test Assessment ' + Date.now());
    await page.getByLabel(/description/i).fill('For detail page testing');
    await page.getByLabel(/overall impact/i).selectOption('Medium');
    
    await page.getByRole('button', { name: /create assessment/i }).click();
    await page.waitForURL(/\/assessments\/[a-f0-9-]+/);
    
    // Extract assessment ID from URL
    assessmentId = page.url().split('/').pop() || '';
    await page.close();
  });

  test('should display assessment details', async ({ page }) => {
    await page.goto(`/assessments/${assessmentId}`);

    // Check header elements
    await expect(page.locator('h1').last()).toBeVisible();
    await expect(page.getByText(/draft|in_review|completed/i)).toBeVisible();
    
    // Check metadata section
    await expect(page.getByText(/overall impact/i)).toBeVisible();
    await expect(page.getByText(/created/i)).toBeVisible();
  });

  test('should have tabs for threats and recommendations', async ({ page }) => {
    await page.goto(`/assessments/${assessmentId}`);
    
    // Check tabs are visible
    await expect(page.getByRole('button', { name: /threats/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /recommendations/i })).toBeVisible();
  });

  test('should switch between tabs', async ({ page }) => {
    await page.goto(`/assessments/${assessmentId}`);
    
    // Click recommendations tab
    await page.getByRole('button', { name: /recommendations/i }).click();
    await expect(page.getByText(/no recommendations yet/i).first()).toBeVisible();
    
    // Click back to threats tab
    await page.getByRole('button', { name: /threats/i }).click();
    await expect(page.getByText(/no threats identified yet/i).first()).toBeVisible();
  });

  test('should have delete button', async ({ page }) => {
    await page.goto(`/assessments/${assessmentId}`);
    
    const deleteButton = page.getByRole('button', { name: /delete/i });
    await expect(deleteButton).toBeVisible();
  });

  test('should have back to assessments link', async ({ page }) => {
    await page.goto(`/assessments/${assessmentId}`);
    
    const backLink = page.getByRole('link', { name: /back to assessments/i });
    await expect(backLink).toBeVisible();
    
    await backLink.click();
    await expect(page).toHaveURL('/assessments');
  });
});
