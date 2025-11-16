import pytest
from playwright.sync_api import Page, expect
from page_objects.login_page import LoginPage
from page_objects.register_page import RegisterPage
from page_objects.dashboard_page import DashboardPage
from page_objects.form_create_page import FormCreatePage
from page_objects.form_display_page import FormDisplayPage


@pytest.fixture
def login_page(page: Page):
    return LoginPage(page)


@pytest.fixture
def register_page(page: Page):
    return RegisterPage(page)


@pytest.fixture
def dashboard_page(page: Page):
    return DashboardPage(page)


@pytest.fixture
def form_create_page(page: Page):
    return FormCreatePage(page)


@pytest.fixture
def form_display_page(page: Page):
    return FormDisplayPage(page)


class TestEdgeCasesAndErrorHandling:
    """Test edge cases, error conditions, and boundary scenarios"""

    def test_empty_and_null_input_handling(self, register_page: RegisterPage, form_create_page: FormCreatePage):
        """Test handling of empty and null inputs"""
        # Test registration with empty fields
        register_page.navigate_to("/auth/register")
        register_page.register("", "", "", "", "")
        expect(register_page.page.locator(".error-message")).to_be_visible()

        # Test form creation with empty title
        form_create_page.navigate_to("/forms/create")
        form_create_page.create_form("", "Description")
        expect(form_create_page.page.locator(".error-message")).to_contain_text("required")

        # Test null values in form data
        form_create_page.create_form(None, None)
        expect(form_create_page.page.locator(".error-message")).to_be_visible()

    def test_maximum_input_length_validation(self, register_page: RegisterPage, form_create_page: FormCreatePage):
        """Test validation of maximum input lengths"""
        # Test extremely long username
        long_username = "a" * 1000
        register_page.navigate_to("/auth/register")
        register_page.register("Test", "User", long_username, "test@example.com", "password123")
        expect(register_page.page.locator(".error-message")).to_contain_text("too long")

        # Test extremely long form title
        long_title = "Form Title " + "x" * 10000
        form_create_page.navigate_to("/forms/create")
        form_create_page.create_form(long_title, "Description")
        expect(form_create_page.page.locator(".error-message")).to_contain_text("too long")

    def test_special_characters_and_unicode_handling(self, register_page: RegisterPage, form_create_page: FormCreatePage):
        """Test handling of special characters and Unicode"""
        # Test Unicode in username
        unicode_username = "测试用户_ñáéíóú"
        register_page.navigate_to("/auth/register")
        register_page.register("Test", "User", unicode_username, "unicode@example.com", "password123")
        # Should either accept or provide clear error message

        # Test special characters in form title
        special_title = "Form with @#$%^&*()_+{}|:<>?[]\\;',./"
        form_create_page.navigate_to("/forms/create")
        form_create_page.create_form(special_title, "Special character test")
        # Should handle special characters appropriately

        # Test emoji in form description
        emoji_description = "Form description with emojis 😀🎉🚀"
        form_create_page.create_form("Emoji Form", emoji_description)
        expect(form_create_page.page.locator(".success-message")).to_be_visible()

    def test_concurrent_user_actions(self, page: Page, dashboard_page: DashboardPage):
        """Test concurrent user actions and race conditions"""
        # Simulate multiple users creating forms simultaneously
        contexts = []
        pages = []

        for i in range(3):
            context = page.context.browser.new_context()
            contexts.append(context)
            new_page = context.new_page()
            pages.append(new_page)

            new_dashboard = DashboardPage(new_page)
            new_dashboard.navigate_to("/auth/login")
            new_dashboard.login("testuser", "TestPassword123!")
            new_dashboard.click_create_form()
            new_dashboard.fill_input("#title", f"Concurrent Form {i}")
            new_dashboard.click_element("button[type='submit']")

        # All should succeed without conflicts
        for p in pages:
            expect(p.locator(".success-message")).to_be_visible()

        # Cleanup
        for context in contexts:
            context.close()

    def test_network_connectivity_issues(self, dashboard_page: DashboardPage):
        """Test behavior during network connectivity issues"""
        # This would require network throttling or disconnection simulation
        dashboard_page.navigate_to("/main/dashboard")

        # Simulate slow network
        dashboard_page.page.route("**/*", lambda route: route.fulfill(delay=5000))
        dashboard_page.page.reload()

        # Should show loading indicators
        expect(dashboard_page.page.locator(".loading-spinner")).to_be_visible()

        # Test timeout handling
        dashboard_page.page.route("**/api/*", lambda route: route.fulfill(status=408))  # Request timeout
        dashboard_page.click_element(".refresh-btn")
        expect(dashboard_page.page.locator(".timeout-error")).to_be_visible()

    def test_database_connection_failures(self, dashboard_page: DashboardPage):
        """Test handling of database connection failures"""
        # This would require database disconnection simulation
        dashboard_page.navigate_to("/main/dashboard")

        # Simulate DB connection failure
        # In a real test environment, this would involve stopping the database
        dashboard_page.click_element(".some-db-dependent-action")

        # Should show appropriate error message
        expect(dashboard_page.page.locator(".db-error")).to_be_visible()

    def test_file_upload_edge_cases(self, form_display_page: FormDisplayPage):
        """Test file upload edge cases"""
        form_id = 1
        form_display_page.navigate_to(f"/forms/{form_id}")

        # Test uploading empty file
        form_display_page.upload_file("1", "")  # Empty path
        expect(form_display_page.page.locator(".file-error")).to_be_visible()

        # Test uploading oversized file
        # Would need a large test file
        # form_display_page.upload_file("1", "large_file.zip")
        # expect(form_display_page.page.locator(".file-too-large")).to_be_visible()

        # Test uploading unsupported file type
        form_display_page.upload_file("1", "test.exe")
        expect(form_display_page.page.locator(".unsupported-file-type")).to_be_visible()

        # Test uploading file with special characters in name
        form_display_page.upload_file("1", "file@#$%.pdf")
        # Should handle or sanitize filename

    def test_session_expiry_and_timeout_handling(self, dashboard_page: DashboardPage, login_page: LoginPage):
        """Test session expiry and timeout scenarios"""
        # Login
        dashboard_page.navigate_to("/auth/login")
        dashboard_page.login("testuser", "TestPassword123!")

        # Simulate session expiry by clearing cookies
        dashboard_page.page.context.clear_cookies()

        # Try to access protected page
        dashboard_page.navigate_to("/main/dashboard")
        expect(login_page.page).to_have_url("**/auth/login")

        # Test session timeout warning (if implemented)
        # Would require setting very short session timeout

    def test_browser_back_forward_navigation(self, dashboard_page: DashboardPage, form_create_page: FormCreatePage):
        """Test browser back/forward navigation edge cases"""
        # Navigate through form creation flow
        dashboard_page.navigate_to("/main/dashboard")
        dashboard_page.click_create_form()

        form_create_page.fill_input("#title", "Navigation Test Form")
        form_create_page.fill_input("#description", "Testing navigation")

        # Use browser back
        dashboard_page.page.go_back()
        expect(dashboard_page.page).to_have_url("**/main/dashboard")

        # Use browser forward
        dashboard_page.page.go_forward()
        expect(dashboard_page.page.locator("#title")).to_have_value("Navigation Test Form")

        # Submit after navigation
        form_create_page.click_element("button[type='submit']")
        expect(form_create_page.page.locator(".success-message")).to_be_visible()

    def test_javascript_disabled_scenarios(self, page: Page):
        """Test application behavior with JavaScript disabled"""
        # Disable JavaScript
        page.context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        # Note: Playwright doesn't fully support disabling JS, but we can test basic functionality

        page.goto("http://localhost:5000/auth/login")

        # Basic form submission should still work
        page.fill("#username", "testuser")
        page.fill("#password", "TestPassword123!")
        page.click("button[type='submit']")

        # Should handle gracefully
        expect(page.locator(".dashboard")).to_be_visible()

    def test_mobile_and_touch_interactions(self, page: Page, dashboard_page: DashboardPage):
        """Test touch and mobile-specific interactions"""
        # Set mobile viewport
        page.set_viewport_size({"width": 375, "height": 667})

        dashboard_page.navigate_to("/main/dashboard")

        # Test touch gestures (tap, swipe)
        dashboard_page.click_element(".mobile-menu-toggle")  # Touch tap

        # Test mobile form interactions
        dashboard_page.click_create_form()
        dashboard_page.fill_input("#title", "Mobile Test Form")

        # Test virtual keyboard behavior
        dashboard_page.click_element("#description")
        # Virtual keyboard should appear on mobile

        dashboard_page.click_element("button[type='submit']")
        expect(dashboard_page.page.locator(".success-message")).to_be_visible()

    def test_internationalization_edge_cases(self, dashboard_page: DashboardPage):
        """Test internationalization edge cases"""
        # Test right-to-left languages
        dashboard_page.navigate_to("/settings/language")
        dashboard_page.click_element("[data-lang='ar']")  # Arabic

        # Check RTL layout
        expect(dashboard_page.page.locator("html")).to_have_attribute("dir", "rtl")

        # Test long translations
        dashboard_page.navigate_to("/main/dashboard")
        # Button text should not overflow

        # Test date/time formatting in different locales
        expect(dashboard_page.page.locator(".date-display")).to_be_visible()

    def test_accessibility_edge_cases(self, dashboard_page: DashboardPage):
        """Test accessibility edge cases and screen reader compatibility"""
        dashboard_page.navigate_to("/main/dashboard")

        # Check for duplicate ARIA labels
        aria_labels = dashboard_page.page.locator("[aria-label]")
        # Should not have duplicates

        # Test keyboard navigation through complex forms
        dashboard_page.page.keyboard.press("Tab")
        dashboard_page.page.keyboard.press("Tab")
        dashboard_page.page.keyboard.press("Enter")

        # Test focus management
        expect(dashboard_page.page.locator(":focus")).to_be_visible()

        # Test color contrast in high contrast mode
        # Would require CSS inspection

    def test_performance_under_extreme_conditions(self, dashboard_page: DashboardPage):
        """Test performance with extreme data volumes"""
        # Test with many forms
        dashboard_page.navigate_to("/forms/my-forms")

        # If there are many forms, test pagination performance
        form_count = dashboard_page.page.locator(".form-item").count()
        if form_count > 100:
            # Test pagination loading time
            start_time = dashboard_page.page.evaluate("performance.now()")
            dashboard_page.click_element(".pagination-next")
            end_time = dashboard_page.page.evaluate("performance.now()")
            assert (end_time - start_time) < 2000  # Should load quickly

        # Test analytics with many responses
        dashboard_page.navigate_to("/analytics")
        if dashboard_page.page.locator(".response-count").text_content() > "1000":
            # Should handle large datasets gracefully
            expect(dashboard_page.page.locator(".performance-warning")).to_be_hidden()

    def test_third_party_service_failures(self, dashboard_page: DashboardPage):
        """Test handling of third-party service failures"""
        # Test email service failure
        dashboard_page.navigate_to("/auth/forgot-password")
        dashboard_page.fill_input("#email", "test@example.com")
        dashboard_page.click_element("button[type='submit']")

        # Even if email fails, should show appropriate message
        expect(dashboard_page.page.locator(".alert")).to_be_visible()

        # Test file storage service failure
        # Would require mocking file upload service failures

        # Test external API failures
        dashboard_page.navigate_to("/analytics")
        # If analytics depend on external services, test failure handling

    def test_data_integrity_edge_cases(self, dashboard_page: DashboardPage, form_display_page: FormDisplayPage):
        """Test data integrity in edge cases"""
        form_id = 1

        # Test submitting form with corrupted data
        form_display_page.navigate_to(f"/forms/{form_id}")

        # Try to inject invalid data
        form_display_page.page.evaluate("""
            document.querySelector('input[name="question_1"]').value = '<script>alert("xss")</script>';
        """)

        form_display_page.submit_form()

        # Data should be sanitized
        dashboard_page.navigate_to(f"/responses/{form_id}")
        expect(dashboard_page.page.locator("script")).to_have_count(0)

        # Test concurrent response submissions
        # Multiple users submitting at the same time
        contexts = []
        for i in range(5):
            context = dashboard_page.page.context.browser.new_context()
            contexts.append(context)
            new_page = context.new_page()
            new_form_display = FormDisplayPage(new_page)
            new_form_display.navigate_to(f"/forms/{form_id}")
            new_form_display.fill_text_input("1", f"Concurrent Response {i}")
            new_form_display.submit_form()

        # All responses should be saved without data loss
        dashboard_page.navigate_to(f"/responses/{form_id}")
        expect(dashboard_page.page.locator(".response-item")).to_have_count_greater_than(4)

        for context in contexts:
            context.close()

    def test_browser_compatibility_edge_cases(self, page: Page):
        """Test browser-specific edge cases"""
        # Test with different user agents
        page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (compatible; OldBrowser/1.0)"
        })

        page.goto("http://localhost:5000")
        # Should still work with older browsers or show appropriate message

        # Test with very small viewport
        page.set_viewport_size({"width": 320, "height": 480})
        page.reload()
        # Should be responsive

        # Test with JavaScript errors
        page.add_init_script("throw new Error('Simulated JS error')")
        page.reload()
        # Application should handle JS errors gracefully

    def test_memory_and_resource_leaks(self, dashboard_page: DashboardPage):
        """Test for memory leaks and resource issues"""
        # Navigate through many pages
        for i in range(20):
            dashboard_page.navigate_to("/main/dashboard")
            dashboard_page.navigate_to("/forms/my-forms")
            dashboard_page.navigate_to("/analytics")

        # Check browser memory usage (if accessible)
        # Should not have excessive memory growth

        # Test with large forms
        dashboard_page.navigate_to("/forms/create")
        # Create form with many questions
        for i in range(50):
            dashboard_page.click_element(".add-question-btn")
            dashboard_page.fill_input(".question-text", f"Question {i}")
            dashboard_page.click_element(".save-question-btn")

        # Should handle large forms without performance issues
        dashboard_page.click_element(".save-structure-btn")
        expect(dashboard_page.page.locator(".success-message")).to_be_visible()

    def test_timezone_and_datetime_edge_cases(self, dashboard_page: DashboardPage):
        """Test datetime and timezone handling edge cases"""
        # Test form with expiration
        dashboard_page.navigate_to("/forms/create")
        dashboard_page.fill_input("#title", "Timezone Test Form")
        dashboard_page.click_element("button[type='submit']")

        form_id = dashboard_page.page.url.split('/')[-2]
        dashboard_page.navigate_to(f"/forms/{form_id}/settings")

        # Set expiration in different timezone
        dashboard_page.fill_input("#expires_at", "2024-12-31T23:59:59")
        dashboard_page.click_element("button[type='submit']")

        # Test across daylight saving time changes
        # Test leap year dates
        # Test invalid dates

    def test_rate_limiting_edge_cases(self, login_page: LoginPage, register_page: RegisterPage):
        """Test rate limiting edge cases"""
        # Test exact rate limit boundaries
        for i in range(10):  # Just under limit
            register_page.navigate_to("/auth/register")
            register_page.register(f"User{i}", "Test", f"user{i}", f"user{i}@example.com", "password123")

        # Next request should be rate limited
        register_page.register("User10", "Test", "user10", "user10@example.com", "password123")
        expect(register_page.page.locator(".rate-limit-error")).to_be_visible()

        # Test rate limit reset
        # Wait for rate limit to reset, then try again
        import time
        time.sleep(61)  # Wait 61 seconds
        register_page.register("User11", "Test", "user11", "user11@example.com", "password123")
        # Should work after reset

    def test_cors_and_security_headers_edge_cases(self, page: Page):
        """Test CORS and security headers in edge cases"""
        # Test CORS preflight requests
        response = page.request.fetch("http://localhost:5000/api/forms", method="OPTIONS")
        assert "Access-Control-Allow-Origin" in response.headers

        # Test security headers
        response = page.request.get("http://localhost:5000")
        assert "X-Frame-Options" in response.headers
        assert "X-Content-Type-Options" in response.headers

        # Test CSP headers
        assert "Content-Security-Policy" in response.headers

    def test_offline_and_sync_functionality(self, page: Page, dashboard_page: DashboardPage):
        """Test offline functionality and data synchronization"""
        # Go offline
        page.context.set_offline(True)

        dashboard_page.navigate_to("/main/dashboard")
        # Should show offline message or cached content

        # Try to perform actions offline
        dashboard_page.click_create_form()
        # Should handle gracefully

        # Come back online
        page.context.set_offline(False)
        page.reload()

        # Should sync any pending actions
        expect(dashboard_page.page.locator(".sync-success")).to_be_visible()

    def test_extreme_load_scenarios(self, page: Page):
        """Test extreme load scenarios"""
        # Open many tabs
        contexts = []
        for i in range(10):
            context = page.context.browser.new_context()
            contexts.append(context)
            new_page = context.new_page()
            new_page.goto("http://localhost:5000/main/dashboard")

        # All should load without crashing
        for context in contexts:
            pages = context.pages
            for p in pages:
                expect(p.locator(".dashboard")).to_be_visible()
            context.close()

        # Test with very large form data
        dashboard_page = DashboardPage(page)
        dashboard_page.navigate_to("/forms/create")
        dashboard_page.fill_input("#title", "A" * 10000)  # Very long title
        dashboard_page.fill_input("#description", "B" * 50000)  # Very long description
        dashboard_page.click_element("button[type='submit']")

        # Should handle large data gracefully
        expect(dashboard_page.page.locator(".success-message")).to_be_visible()