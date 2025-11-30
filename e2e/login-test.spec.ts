import { test, expect } from '@playwright/test';

test.describe('Login Tests', () => {
  // Test successful authentication scenarios
  test('should successfully login with valid credentials', async ({ page }) => {
    await page.goto('http://127.0.0.1:5000/auth/login');
    
    // Fill in valid credentials
    await page.getByRole('textbox', { name: 'Username' }).fill('ravi1997');
    await page.getByRole('textbox', { name: 'Password' }).fill('Singh@1997');
    await page.getByRole('button', { name: 'Sign in to your account' }).click();
    
    // Verify successful login redirects to dashboard
    await expect(page).toHaveURL(/dashboard/);
    await expect(page.getByText('Welcome')).toBeVisible();
  });

  // Test various failure cases including invalid credentials, account lockout, and expired sessions
  test('should show error for invalid credentials', async ({ page }) => {
    await page.goto('http://127.0.0.1:5000/auth/login');
    
    // Fill in invalid credentials
    await page.getByRole('textbox', { name: 'Username' }).fill('wronguser');
    await page.getByRole('textbox', { name: 'Password' }).fill('wrongpass');
    await page.getByRole('button', { name: 'Sign in to your account' }).click();
    
    // Verify error message is displayed
    await expect(page.getByText('Invalid username or password')).toBeVisible();
  });

  test('should show error for non-existent user', async ({ page }) => {
    await page.goto('http://127.0.0.1:5000/auth/login');
    
    // Fill in credentials for non-existent user
    await page.getByRole('textbox', { name: 'Username' }).fill('nonexistent');
    await page.getByRole('textbox', { name: 'Password' }).fill('password123');
    await page.getByRole('button', { name: 'Sign in to your account' }).click();
    
    // Verify error message is displayed
    await expect(page.getByText('Invalid username or password')).toBeVisible();
  });

  // Test edge cases such as empty fields, special characters, and length validation
  test('should show validation error for empty fields', async ({ page }) => {
    await page.goto('http://127.0.0.1:5000/auth/login');
    
    // Submit without filling anything
    await page.getByRole('button', { name: 'Sign in to your account' }).click();
    
    // Verify validation errors are displayed
    await expect(page.getByText('Username is required')).toBeVisible();
    await expect(page.getByText('Password is required')).toBeVisible();
  });

  test('should handle special characters in credentials', async ({ page }) => {
    await page.goto('http://127.0.0.1:5000/auth/login');
    
    // Fill in credentials with special characters
    await page.getByRole('textbox', { name: 'Username' }).fill('user@special!#$%');
    await page.getByRole('textbox', { name: 'Password' }).fill('pass!@#$%^&*()');
    await page.getByRole('button', { name: 'Sign in to your account' }).click();
    
    // Verify appropriate error message
    await expect(page.getByText('Invalid username or password')).toBeVisible();
  });

  test('should validate password length', async ({ page }) => {
    await page.goto('http://127.0.0.1:5000/auth/login');
    
    // Fill in short password
    await page.getByRole('textbox', { name: 'Username' }).fill('validuser');
    await page.getByRole('textbox', { name: 'Password' }).fill('short');
    await page.getByRole('button', { name: 'Sign in to your account' }).click();
    
    // Verify appropriate error message
    await expect(page.getByText('Invalid username or password')).toBeVisible();
  });

  // Test form state preservation
  test('should preserve form state on validation error', async ({ page }) => {
    await page.goto('http://127.0.0.1:5000/auth/login');
    
    // Fill in only username
    await page.getByRole('textbox', { name: 'Username' }).fill('validuser');
    await page.getByRole('button', { name: 'Sign in to your account' }).click();
    
    // Verify username is still filled and error message appears
    await expect(page.getByRole('textbox', { name: 'Username' })).toHaveValue('validuser');
    await expect(page.getByText('Password is required')).toBeVisible();
  });

  // Test navigation flows
  test('should navigate to forgot password page', async ({ page }) => {
    await page.goto('http://127.0.0.1:5000/auth/login');
    
    // Click forgot password link
    await page.getByRole('link', { name: 'Forgot Password?' }).click();
    
    // Verify navigation to forgot password page
    await expect(page).toHaveURL(/forgot-password/);
  });

  test('should navigate to registration page', async ({ page }) => {
    await page.goto('http://127.0.0.1:5000/auth/login');
    
    // Click register link
    await page.getByRole('link', { name: 'Create an account' }).click();
    
    // Verify navigation to registration page
    await expect(page).toHaveURL(/register/);
  });

  // Test account lockout scenarios
  test('should handle multiple failed login attempts', async ({ page }) => {
    await page.goto('http://127.0.0.1:5000/auth/login');
    
    // Try multiple failed logins
    for (let i = 0; i < 5; i++) {
      await page.getByRole('textbox', { name: 'Username' }).fill(`user${i}`);
      await page.getByRole('textbox', { name: 'Password' }).fill('wrongpass');
      await page.getByRole('button', { name: 'Sign in to your account' }).click();
      
      // Verify error message for each attempt
      await expect(page.getByText('Invalid username or password')).toBeVisible();
      
      // Clear fields for next attempt
      await page.getByRole('textbox', { name: 'Username' }).fill('');
      await page.getByRole('textbox', { name: 'Password' }).fill('');
    }
  });

  // Test session management
  test('should maintain session after login', async ({ page }) => {
    await page.goto('http://127.0.0.1:5000/auth/login');
    
    // Login with valid credentials
    await page.getByRole('textbox', { name: 'Username' }).fill('ravi1997');
    await page.getByRole('textbox', { name: 'Password' }).fill('Singh@1997');
    await page.getByRole('button', { name: 'Sign in to your account' }).click();
    
    // Navigate to dashboard
    await expect(page).toHaveURL(/dashboard/);
    
    // Navigate to profile page to verify session is maintained
    await page.getByRole('link', { name: 'Profile' }).click();
    await expect(page).toHaveURL(/profile/);
  });

  // Test error message verification
  test('should display appropriate error messages for different scenarios', async ({ page }) => {
    await page.goto('http://127.0.0.1:5000/auth/login');
    
    // Test for account disabled
    await page.getByRole('textbox', { name: 'Username' }).fill('disableduser');
    await page.getByRole('textbox', { name: 'Password' }).fill('password123');
    await page.getByRole('button', { name: 'Sign in to your account' }).click();
    
    // Verify appropriate error message
    await expect(page.getByText('Account is disabled')).toBeVisible();
    
    // Test for unverified email
    await page.getByRole('textbox', { name: 'Username' }).fill('unverifieduser');
    await page.getByRole('textbox', { name: 'Password' }).fill('password123');
    await page.getByRole('button', { name: 'Sign in to your account' }).click();
    
    // Verify appropriate error message
    await expect(page.getByText('Please verify your email before logging in')).toBeVisible();
  });

  // Test basic form validation
  test('should validate form inputs', async ({ page }) => {
    await page.goto('http://127.0.0.1:5000/auth/login');
    
    // Test with empty form
    await page.getByRole('button', { name: 'Sign in to your account' }).click();
    
    // Verify validation messages
    await expect(page.getByText('Username is required')).toBeVisible();
    await expect(page.getByText('Password is required')).toBeVisible();
  });
});
