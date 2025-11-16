import pytest
from playwright.sync_api import Page, expect
from page_objects.login_page import LoginPage
from page_objects.register_page import RegisterPage
from page_objects.dashboard_page import DashboardPage


@pytest.fixture
def login_page(page: Page):
    return LoginPage(page)


@pytest.fixture
def register_page(page: Page):
    return RegisterPage(page)


@pytest.fixture
def dashboard_page(page: Page):
    return DashboardPage(page)


class TestAuthentication:
    """Test authentication flows including registration, login, password reset, and email verification"""

    def test_successful_user_registration(self, register_page: RegisterPage):
        """Test successful user registration with email verification"""
        # Navigate to registration page
        register_page.navigate_to("/auth/register")

        # Generate unique test data
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        test_user = {
            "first_name": "Test",
            "last_name": "User",
            "username": f"testuser_{unique_id}",
            "email": f"testuser_{unique_id}@example.com",
            "password": "TestPassword123!"
        }

        # Fill registration form
        register_page.register(
            first_name=test_user["first_name"],
            last_name=test_user["last_name"],
            username=test_user["username"],
            email=test_user["email"],
            password=test_user["password"]
        )

        # Assert registration success message
        register_page.assert_registration_success()

    def test_registration_validation_errors(self, register_page: RegisterPage):
        """Test registration form validation errors"""
        register_page.navigate_to("/auth/register")

        # Test empty form submission
        register_page.register("", "", "", "", "")
        register_page.assert_validation_error("Username is required")

        # Test duplicate username (assuming a user exists)
        register_page.register("Test", "User", "existinguser", "new@example.com", "password123")
        register_page.assert_registration_failed("Username already exists")

        # Test duplicate email
        register_page.register("Test", "User", "newuser", "existing@example.com", "password123")
        register_page.assert_registration_failed("Email already registered")

        # Test weak password
        register_page.register("Test", "User", "newuser2", "new2@example.com", "123")
        register_page.assert_validation_error("Password must be at least 8 characters")

    def test_successful_login(self, login_page: LoginPage, dashboard_page: DashboardPage):
        """Test successful user login"""
        # Assuming we have a test user created
        login_page.navigate_to("/auth/login")

        login_page.login("testuser", "TestPassword123!")

        # Assert login success
        login_page.assert_login_success()
        dashboard_page.assert_dashboard_accessible()

    def test_login_validation_errors(self, login_page: LoginPage):
        """Test login form validation and error handling"""
        login_page.navigate_to("/auth/login")

        # Test invalid credentials
        login_page.login("nonexistent", "wrongpassword")
        login_page.assert_login_failed("Invalid username or password")

        # Test empty fields
        login_page.login("", "")
        login_page.assert_login_failed()

        # Test unverified account
        login_page.login("unverifieduser", "password123")
        login_page.assert_login_failed("Please verify your email before logging in")

        # Test disabled account
        login_page.login("disableduser", "password123")
        login_page.assert_login_failed("Account is disabled")

    def test_password_reset_flow(self, login_page: LoginPage):
        """Test password reset request and completion"""
        login_page.navigate_to("/auth/login")

        # Navigate to forgot password
        login_page.go_to_forgot_password()

        # Request password reset
        login_page.fill_input("#email", "testuser@example.com")
        login_page.click_element("button[type='submit']")

        # Assert reset email sent message
        expect(login_page.page.locator(".alert-success")).to_contain_text("If the email exists")

        # Note: Email verification and token-based reset would require email interception
        # For full E2E testing, consider using email testing services

    def test_navigation_between_auth_pages(self, login_page: LoginPage, register_page: RegisterPage):
        """Test navigation between login and registration pages"""
        # Start at login page
        login_page.navigate_to("/auth/login")

        # Navigate to registration
        login_page.go_to_register()
        expect(register_page.page).to_have_url("**/auth/register")

        # Navigate back to login
        register_page.go_to_login()
        expect(login_page.page).to_have_url("**/auth/login")

    def test_logout_functionality(self, login_page: LoginPage, dashboard_page: DashboardPage):
        """Test user logout functionality"""
        # Login first
        login_page.navigate_to("/auth/login")
        login_page.login("testuser", "TestPassword123!")
        dashboard_page.assert_dashboard_accessible()

        # Logout
        dashboard_page.logout()

        # Assert redirected to login or home page
        expect(login_page.page).to_have_url(re.compile(r"/auth/login|/"))

        # Verify user is logged out (no dashboard access)
        dashboard_page.navigate_to("/main/dashboard")
        expect(login_page.page).to_have_url("**/auth/login")

    def test_session_persistence(self, page: Page, login_page: LoginPage, dashboard_page: DashboardPage):
        """Test that user session persists across page reloads"""
        # Login
        login_page.navigate_to("/auth/login")
        login_page.login("testuser", "TestPassword123!")
        dashboard_page.assert_dashboard_accessible()

        # Reload page
        page.reload()
        dashboard_page.wait_for_load()

        # Assert still logged in
        dashboard_page.assert_dashboard_accessible()

    def test_concurrent_login_sessions(self, page: Page, login_page: LoginPage):
        """Test behavior with multiple login sessions (if applicable)"""
        # This test would require multiple browser contexts
        # For now, test basic session handling
        login_page.navigate_to("/auth/login")
        login_page.login("testuser", "TestPassword123!")

        # Open new context (simulating another browser)
        context = page.context.browser.new_context()
        new_page = context.new_page()
        new_login_page = LoginPage(new_page)

        new_login_page.navigate_to("/auth/login")
        new_login_page.login("testuser", "TestPassword123!")

        # Both should work (assuming no session limits)
        expect(new_page).to_have_url(re.compile(r"/main/dashboard|/dashboard"))

        context.close()

    @pytest.mark.parametrize("browser_name", ["chromium", "firefox", "webkit"])
    def test_cross_browser_authentication(self, page: Page, browser_name: str):
        """Test authentication works across different browsers"""
        login_page = LoginPage(page)

        login_page.navigate_to("/auth/login")
        login_page.login("testuser", "TestPassword123!")

        # Assert login works regardless of browser
        expect(page).to_have_url(re.compile(r"/main/dashboard|/dashboard"))

    def test_rate_limiting_on_auth_endpoints(self, login_page: LoginPage, register_page: RegisterPage):
        """Test rate limiting on authentication endpoints"""
        # Test login rate limiting
        for i in range(15):  # Exceed the limit
            login_page.navigate_to("/auth/login")
            login_page.login("testuser", "wrongpassword")
            if i > 10:  # After rate limit kicks in
                expect(login_page.page.locator(".alert-danger")).to_contain_text("Too many requests")

        # Test registration rate limiting
        for i in range(10):
            register_page.navigate_to("/auth/register")
            register_page.register("Test", "User", f"user{i}", f"user{i}@example.com", "password123")
            if i > 5:
                expect(register_page.page.locator(".alert-danger")).to_contain_text("Too many requests")

    def test_sql_injection_prevention(self, login_page: LoginPage):
        """Test that SQL injection attempts are prevented"""
        login_page.navigate_to("/auth/login")

        # Test SQL injection in username
        login_page.login("'; DROP TABLE users; --", "password")
        login_page.assert_login_failed("Invalid username or password")

        # Test in password field
        login_page.login("testuser", "' OR '1'='1")
        login_page.assert_login_failed("Invalid username or password")

    def test_xss_prevention_in_auth_forms(self, register_page: RegisterPage):
        """Test that XSS attempts in auth forms are prevented"""
        register_page.navigate_to("/auth/register")

        # Test XSS in username
        xss_payload = "<script>alert('xss')</script>"
        register_page.register("Test", "User", xss_payload, "test@example.com", "password123")

        # Assert no script execution (page should not show alert)
        # This is basic - more sophisticated XSS testing would require additional tools
        expect(register_page.page.locator("script")).to_have_count(0)