import { test, expect } from '@playwright/test';

test('registeration test', async ({ page }) => {
  await page.goto('http://127.0.0.1:5000/auth/register');
  await page.getByRole('textbox', { name: 'First Name' }).click();
  await page.getByRole('textbox', { name: 'First Name' }).fill('ravinder');
  await page.getByRole('textbox', { name: 'Last Name' }).fill('Singh');
  await page.getByRole('textbox', { name: 'Username' }).fill('ravi1997');
  await page.getByRole('textbox', { name: 'Email' }).fill('ravi199777@gmail.com');
  await page.getByRole('textbox', { name: 'Password' }).fill('Singh@1997');
  await page.getByRole('button', { name: ' Create Account' }).click();
});