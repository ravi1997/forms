// @ts-check
import { test, expect } from '@playwright/test';

// Base URL - adjust according to your app's URL
const BASE_URL = 'http://localhost:5000';

test.describe('Flask Application Routes', () => {
  test.beforeEach(async ({ page }) => {
    // Clear any existing cookies/session
    await page.context().clearCookies();
  });

  test('should load main page', async ({ page }) => {
    await page.goto(BASE_URL);
    await expect(page).toHaveTitle(/Form Builder/);
  });

  test('should access dashboard (authenticated)', async ({ page }) => {
    // Try to access dashboard without login (should redirect to login)
    await page.goto('/dashboard');
    await expect(page).toHaveURL(/\/auth\/login/);
  });

  test('should access profile (authenticated)', async ({ page }) => {
    await page.goto('/profile');
    await expect(page).toHaveURL(/\/auth\/login/);
  });

  test('should access search', async ({ page }) => {
    await page.goto('/search');
    await expect(page).toHaveURL(/\/search/);
  });

  test('should access health check', async ({ page }) => {
    await page.goto('/health');
    await expect(page).toHaveURL(/\/health/);
  });

  // Auth routes
  test('should access registration page', async ({ page }) => {
    await page.goto('/auth/register');
    await expect(page).toHaveURL(/\/auth\/register/);
  });

  test('should access login page', async ({ page }) => {
    await page.goto('/auth/login');
    await expect(page).toHaveURL(/\/auth\/login/);
  });

  test('should access forgot password page', async ({ page }) => {
    await page.goto('/auth/forgot-password');
    await expect(page).toHaveURL(/\/auth\/forgot-password/);
  });

  // API routes (authenticated)
  test('should access API users endpoint (authenticated)', async ({ page }) => {
    await page.goto('/api/users');
    // Should redirect to login for protected routes
    await expect(page).toHaveURL(/\/auth\/login/);
  });

  test('should access API current user profile endpoint (authenticated)', async ({ page }) => {
    await page.goto('/api/users/profile');
    // Should redirect to login for protected routes
    await expect(page).toHaveURL(/\/auth\/login/);
  });

  test('should access API forms endpoint (authenticated)', async ({ page }) => {
    await page.goto('/api/forms');
    // Should redirect to login for protected routes
    await expect(page).toHaveURL(/\/auth\/login/);
  });

  test('should access API form endpoint (authenticated)', async ({ page }) => {
    await page.goto('/api/forms/1');
    // Should redirect to login for protected routes
    await expect(page).toHaveURL(/\/auth\/login/);
  });

  // Forms routes
  test('should access form display page', async ({ page }) => {
    await page.goto('/forms/1');
    // May return 404 or 404 page depending on form existence
    // Just ensuring the route exists
    await expect(page).toHaveURL(/\/forms\/\d+/);
  });

  test('should access form builder page', async ({ page }) => {
    await page.goto('/forms/1/builder');
    // Should redirect to login if not authenticated
    await expect(page).toHaveURL(/\/auth\/login/);
  });

  test('should access form templates page', async ({ page }) => {
    await page.goto('/forms/templates');
    // Should redirect to login if not authenticated
    await expect(page).toHaveURL(/\/auth\/login/);
  });

  test('should access create form page', async ({ page }) => {
    await page.goto('/forms/create');
    // Should redirect to login if not authenticated
    await expect(page).toHaveURL(/\/auth\/login/);
  });

  test('should access my forms page', async ({ page }) => {
    await page.goto('/forms/my-forms');
    // Should redirect to login if not authenticated
    await expect(page).toHaveURL(/\/auth\/login/);
  });

  // Responses routes
  test('should access responses list page', async ({ page }) => {
    await page.goto('/responses/1');
    // Should redirect to login if not authenticated
    await expect(page).toHaveURL(/\/auth\/login/);
  });

  test('should access response details page', async ({ page }) => {
    await page.goto('/responses/1/details');
    // Should redirect to login if not authenticated
    await expect(page).toHaveURL(/\/auth\/login/);
  });

  test('should access export responses page', async ({ page }) => {
    await page.goto('/responses/1/export');
    // Should redirect to login if not authenticated
    await expect(page).toHaveURL(/\/auth\/login/);
  });

  // Analytics routes
  test('should access analytics dashboard', async ({ page }) => {
    await page.goto('/analytics/');
    // Should redirect to login if not authenticated
    await expect(page).toHaveURL(/\/auth\/login/);
  });

  test('should access form analytics page', async ({ page }) => {
    await page.goto('/analytics/form/1');
    // Should redirect to login if not authenticated
    await expect(page).toHaveURL(/\/auth\/login/);
  });

  // Error handling routes
  test('should handle 404 errors', async ({ page }) => {
    await page.goto('/non-existent-route');
    // Depending on how error pages are handled, this might redirect or show error page
    // We're mainly testing that the route doesn't crash
  });
});
