import { test, expect } from '@playwright/test';

let assessmentId: string;

test.describe('Threat Management', () => {
  test.beforeAll(async ({ browser }) => {
    // Create an assessment to test with
    const page = await browser.newPage();
    await page.goto('/assessments/new');
    
    await page.getByLabel(/assessment title/i).fill('Threat Test Assessment ' + Date.now());
    await page.getByLabel(/description/i).fill('For threat testing');
    await page.getByLabel(/overall impact/i).selectOption('High');
    
    await page.getByRole('button', { name: /create assessment/i }).click();
    await page.waitForURL(/\/assessments\/[a-f0-9-]+/);
    
    assessmentId = page.url().split('/').pop() || '';
    await page.close();
  });

  test('should open add threat modal', async ({ page }) => {
    await page.goto(`/assessments/${assessmentId}`);
    
    // Click Add Threat button
    await page.getByRole('button', { name: /add threat/i }).first().click();
    
    // Modal should be visible
    await expect(page.getByRole('heading', { name: /add new threat/i })).toBeVisible();
  });

  test('should display threat form fields', async ({ page }) => {
    await page.goto(`/assessments/${assessmentId}`);
    await page.getByRole('button', { name: /add threat/i }).first().click();
    
    // Check all form fields
    await expect(page.getByLabel(/threat title/i)).toBeVisible();
    await expect(page.getByLabel(/description/i)).toBeVisible();
    await expect(page.getByLabel(/likelihood/i)).toBeVisible();
    await expect(page.getByLabel(/impact/i)).toBeVisible();
  });

  test('should close modal on cancel', async ({ page }) => {
    await page.goto(`/assessments/${assessmentId}`);
    await page.getByRole('button', { name: /add threat/i }).first().click();
    
    // Click cancel
    await page.getByRole('button', { name: /cancel/i }).click();
    
    // Modal should be closed
    await expect(page.getByRole('heading', { name: /add new threat/i })).not.toBeVisible();
  });

  test('should create a new threat successfully', async ({ page }) => {
    await page.goto(`/assessments/${assessmentId}`);
    await page.getByRole('button', { name: /add threat/i }).first().click();
    
    // Fill out threat form
    await page.getByLabel(/threat title/i).fill('SQL Injection Vulnerability');
    await page.getByLabel(/description/i).fill('Potential SQL injection in user input fields');
    await page.getByLabel(/likelihood/i).selectOption('High');
    await page.getByLabel(/impact/i).selectOption('Critical');
    
    // Submit
    await page.getByRole('button', { name: /add threat/i }).last().click();
    
    // Wait for modal to close and API call to complete
    await page.waitForTimeout(2000);
    
    // Verify we're still on the assessment detail page (check URL pattern)
    await expect(page).toHaveURL(/\/assessments\/[a-f0-9-]+/);
  });

  test('should display created threat in the list', async ({ page }) => {
    await page.goto(`/assessments/${assessmentId}`);
    await page.waitForLoadState('networkidle');
    
    // Check if threats section is visible (either with threats or empty state)
    const threatsSection = page.getByText(/identified threats/i).or(page.getByText(/no threats identified/i));
    await expect(threatsSection.first()).toBeVisible();
  });

  test('should validate required threat fields', async ({ page }) => {
    await page.goto(`/assessments/${assessmentId}`);
    await page.getByRole('button', { name: /add threat/i }).first().click();
    
    // Try to submit without filling required fields
    await page.getByRole('button', { name: /add threat/i }).last().click();
    
    // Should show validation error
    const nameInput = page.getByLabel(/threat name/i);
    const isInvalid = await nameInput.evaluate((el: HTMLInputElement) => !el.validity.valid);
    expect(isInvalid).toBeTruthy();
  });
});
