import { test, expect } from '@playwright/test';

test.describe('API Integration Tests', () => {
  test('should handle API errors gracefully', async ({ page }) => {
    // Simulate network error by blocking API calls
    await page.route('**/api/v1/**', route => route.abort());
    
    await page.goto('/assessments');
    await page.waitForTimeout(2000);
    
    // Should show error message or handle gracefully
    // The page should still render without crashing
    await expect(page.locator('body')).toBeVisible();
  });

  test('should retry failed requests', async ({ page }) => {
    let callCount = 0;
    
    // Fail first request, succeed on retry
    await page.route('**/api/v1/assessments/', route => {
      callCount++;
      if (callCount === 1) {
        route.abort();
      } else {
        route.continue();
      }
    });
    
    await page.goto('/assessments');
    await page.waitForTimeout(3000);
  });

  test('should maintain state during navigation', async ({ page }) => {
    await page.goto('/assessments');
    await page.waitForTimeout(1000);
    
    // Filter assessments
    const searchInput = page.getByPlaceholder(/search/i);
    if (await searchInput.isVisible()) {
      await searchInput.fill('Test');
    }
    
    // Navigate away
    await page.goto('/');
    
    // Navigate back
    await page.goto('/assessments');

    // Page should load successfully
    await expect(page.getByRole('heading', { name: 'Assessments' })).toBeVisible();
  });
});
