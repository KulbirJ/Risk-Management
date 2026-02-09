import { test, expect } from '@playwright/test';

test.describe('Create Assessment', () => {
  test('should navigate to new assessment form', async ({ page }) => {
    await page.goto('/assessments');
    
    const newButton = page.getByRole('link', { name: /new assessment/i });
    await newButton.click();
    
    await expect(page).toHaveURL('/assessments/new');
    await expect(page.getByRole('heading', { name: 'New Assessment' })).toBeVisible();
  });

  test('should display all required form fields', async ({ page }) => {
    await page.goto('/assessments/new');
    
    // Check all form fields are present
    await expect(page.getByLabel(/assessment title/i)).toBeVisible();
    await expect(page.getByLabel(/description/i)).toBeVisible();
    await expect(page.getByLabel(/system background/i)).toBeVisible();
    await expect(page.getByLabel(/scope/i)).toBeVisible();
    await expect(page.getByLabel(/technology stack/i)).toBeVisible();
    await expect(page.getByLabel(/overall impact/i)).toBeVisible();
  });

  test('should create a new assessment successfully', async ({ page }) => {
    await page.goto('/assessments/new');
    
    // Fill out the form
    await page.getByLabel(/assessment title/i).fill('E2E Test Assessment ' + Date.now());
    await page.getByLabel(/description/i).fill('This is an automated test assessment');
    await page.getByLabel(/system background/i).fill('Testing environment with containerized services');
    await page.getByLabel(/scope/i).fill('Full stack web application security assessment');
    await page.getByLabel(/technology stack/i).fill('Next.js, FastAPI, PostgreSQL, Docker');
    await page.getByLabel(/overall impact/i).selectOption('High');
    
    // Submit the form
    await page.getByRole('button', { name: /create assessment/i }).click();
    
    // Should redirect to assessment detail page
    await expect(page).toHaveURL(/\/assessments\/[a-f0-9-]+/, { timeout: 10000 });
    await expect(page.getByText(/E2E Test Assessment/)).toBeVisible();
  });

  test('should validate required fields', async ({ page }) => {
    await page.goto('/assessments/new');
    
    // Try to submit empty form
    await page.getByRole('button', { name: /create assessment/i }).click();
    
    // Should show validation error (browser's built-in validation)
    const titleInput = page.getByLabel(/assessment title/i);
    const isInvalid = await titleInput.evaluate((el: HTMLInputElement) => !el.validity.valid);
    expect(isInvalid).toBeTruthy();
  });

  test('should have cancel button that navigates back', async ({ page }) => {
    await page.goto('/assessments/new');

    const cancelButton = page.getByRole('link', { name: /cancel/i }).first();
    await expect(cancelButton).toBeVisible();

    await cancelButton.click();
    await expect(page).toHaveURL('/assessments');
  });
});
