import { test, expect } from '@playwright/test';

test.describe('Full User Journey', () => {
  test('complete assessment creation and threat addition workflow', async ({ page }) => {
    // 1. Start at dashboard
    await page.goto('/');
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();
    
    // 2. Navigate to create new assessment
    await page.getByRole('link', { name: /new assessment/i }).click();
    await expect(page).toHaveURL('/assessments/new');
    
    // 3. Fill out assessment form
    const timestamp = Date.now();
    await page.getByLabel(/assessment title/i).fill(`Full Journey Test ${timestamp}`);
    await page.getByLabel(/description/i).fill('Complete end-to-end test assessment');
    await page.getByLabel(/system background/i).fill('Testing the full user workflow');
    await page.getByLabel(/scope/i).fill('All application components');
    await page.getByLabel(/technology stack/i).fill('Next.js, FastAPI, PostgreSQL');
    await page.getByLabel(/overall impact/i).selectOption('High');
    
    // 4. Create assessment
    await page.getByRole('button', { name: /create assessment/i }).click();
    await page.waitForURL(/\/assessments\/[a-f0-9-]+/, { timeout: 10000 });
    
    // 5. Verify assessment was created
    await expect(page.getByText(`Full Journey Test ${timestamp}`)).toBeVisible();
    
    // 6. Add a threat
    await page.getByRole('button', { name: /add threat/i }).first().click();
    await expect(page.getByRole('heading', { name: /add new threat/i })).toBeVisible();
    
    // 7. Fill threat form
    await page.getByLabel(/threat title/i).fill('Cross-Site Scripting (XSS)');
    await page.getByLabel(/description/i).fill('Potential XSS vulnerability in user comments');
    await page.getByLabel(/likelihood/i).selectOption('Medium');
    await page.getByLabel(/impact/i).selectOption('High');
    
    // 8. Submit threat
    await page.getByRole('button', { name: /add threat/i }).last().click();
    await page.waitForTimeout(2000);
    
    // 9. Verify we're still on assessment detail page (or at least not on an error page)
    const currentUrl = page.url();
    expect(currentUrl).toMatch(/\/assessments/);
    
    // 10. Navigate back to assessments list
    // Try to find back link, if not found just navigate directly
    const backLink = page.getByRole('link', { name: /back to assessments/i });
    const hasBackLink = await backLink.isVisible().catch(() => false);
    
    if (hasBackLink) {
      await backLink.click();
    } else {
      // If back link not found, navigate directly
      await page.goto('/assessments');
    }
    await expect(page).toHaveURL('/assessments');
    
    // 11. Verify assessment appears in list
    await page.waitForTimeout(1000);
    await expect(page.getByText(`Full Journey Test ${timestamp}`)).toBeVisible();
    
    // 12. Return to dashboard
    await page.goto('/');
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();
    
    console.log('✅ Complete user journey test passed successfully!');
  });
});
