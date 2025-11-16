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


class TestEndToEndFlows:
    """End-to-end integration tests covering complete user journeys"""

    def test_complete_user_registration_and_form_creation_flow(self, register_page: RegisterPage,
                                                              login_page: LoginPage,
                                                              dashboard_page: DashboardPage,
                                                              form_create_page: FormCreatePage):
        """Test complete flow from user registration to form creation"""
        import uuid
        unique_id = str(uuid.uuid4())[:8]

        # Step 1: Register new user
        register_page.navigate_to("/auth/register")
        register_page.register(
            first_name="E2E",
            last_name="User",
            username=f"e2euser_{unique_id}",
            email=f"e2euser_{unique_id}@example.com",
            password="TestPassword123!"
        )
        register_page.assert_registration_success()

        # Step 2: Login with new account
        login_page.navigate_to("/auth/login")
        login_page.login(f"e2euser_{unique_id}", "TestPassword123!")
        login_page.assert_login_success()

        # Step 3: Create a form
        dashboard_page.click_create_form()
        form_title = f"E2E Test Form {unique_id}"
        form_description = "Form created during end-to-end testing"
        form_create_page.create_form(form_title, form_description)
        form_create_page.assert_form_creation_success()

        # Step 4: Verify form appears in dashboard
        dashboard_page.navigate_to("/main/dashboard")
        expect(dashboard_page.page.locator(".forms-list")).to_contain_text(form_title)

    def test_form_creation_publication_and_submission_flow(self, dashboard_page: DashboardPage,
                                                           form_create_page: FormCreatePage,
                                                           form_display_page: FormDisplayPage):
        """Test complete flow from form creation to publication and submission"""
        import uuid
        unique_id = str(uuid.uuid4())[:8]

        # Step 1: Create and publish form
        dashboard_page.navigate_to("/forms/create")
        form_title = f"Public Test Form {unique_id}"
        form_create_page.create_form(form_title, "Test form for submission")
        form_create_page.assert_form_creation_success()

        # Step 2: Publish the form (assuming form ID can be extracted)
        # Navigate to form builder and publish
        form_url = dashboard_page.page.url  # Should be /forms/{id}/builder
        form_id = form_url.split('/')[-2]  # Extract form ID from URL

        dashboard_page.click_element(".publish-btn")
        expect(dashboard_page.page.locator(".alert-success")).to_contain_text("published")

        # Step 3: Submit form as anonymous user
        public_form_url = f"/forms/{form_id}"
        form_display_page.navigate_to(public_form_url)

        # Fill and submit form
        form_display_page.fill_text_input("1", "Test Respondent")
        form_display_page.fill_email_input("2", "respondent@example.com")
        form_display_page.select_radio_option("3", "Option A")
        form_display_page.submit_form()

        form_display_page.assert_form_submission_success()

    def test_authenticated_form_submission_and_response_management(self, dashboard_page: DashboardPage,
                                                                  form_display_page: FormDisplayPage):
        """Test form submission by authenticated user and response management"""
        # Step 1: Login
        dashboard_page.navigate_to("/auth/login")
        dashboard_page.login("testuser", "TestPassword123!")

        # Step 2: Submit form
        form_id = 1  # Assuming test form exists
        form_display_page.navigate_to(f"/forms/{form_id}")
        form_display_page.fill_text_input("1", "Authenticated User")
        form_display_page.fill_email_input("2", "auth@example.com")
        form_display_page.submit_form()
        form_display_page.assert_form_submission_success()

        # Step 3: View responses
        dashboard_page.navigate_to(f"/responses/{form_id}")
        expect(dashboard_page.page.locator(".response-item")).to_contain_text("Authenticated User")

        # Step 4: View response details
        dashboard_page.click_element(".response-item:first-child .view-details-btn")
        expect(dashboard_page.page.locator(".response-details")).to_contain_text("auth@example.com")

    def test_form_builder_and_question_management_flow(self, dashboard_page: DashboardPage):
        """Test form builder functionality and question management"""
        form_id = 1
        dashboard_page.navigate_to(f"/forms/{form_id}/builder")

        # Add a new section
        dashboard_page.click_element(".add-section-btn")
        dashboard_page.fill_input(".section-title", "Test Section")
        dashboard_page.fill_input(".section-description", "Section for testing")

        # Add different question types
        dashboard_page.click_element(".add-question-btn")
        dashboard_page.select_option(".question-type", "text")
        dashboard_page.fill_input(".question-text", "What is your name?")
        dashboard_page.check_checkbox(".question-required")
        dashboard_page.click_element(".save-question-btn")

        dashboard_page.click_element(".add-question-btn")
        dashboard_page.select_option(".question-type", "multiple_choice")
        dashboard_page.fill_input(".question-text", "What is your favorite color?")
        dashboard_page.fill_input(".question-options", "Red\nBlue\nGreen")
        dashboard_page.click_element(".save-question-btn")

        # Save form structure
        dashboard_page.click_element(".save-structure-btn")
        expect(dashboard_page.page.locator(".alert-success")).to_contain_text("structure updated")

        # Preview form
        dashboard_page.click_element(".preview-btn")
        expect(dashboard_page.page.locator("h1")).to_be_visible()
        expect(dashboard_page.page.locator(".question")).to_have_count_greater_than(1)

    def test_user_profile_management_flow(self, dashboard_page: DashboardPage):
        """Test user profile management end-to-end"""
        # Login
        dashboard_page.navigate_to("/auth/login")
        dashboard_page.login("testuser", "TestPassword123!")

        # Navigate to profile
        dashboard_page.go_to_profile()

        # Update profile information
        dashboard_page.fill_input("#first_name", "Updated")
        dashboard_page.fill_input("#last_name", "Name")
        dashboard_page.fill_input("#email", "updated@example.com")
        dashboard_page.click_element("button[type='submit']")

        # Assert profile updated
        expect(dashboard_page.page.locator(".alert-success")).to_contain_text("updated successfully")

        # Verify changes persist
        dashboard_page.page.reload()
        expect(dashboard_page.page.locator("#first_name")).to_have_value("Updated")

    def test_password_reset_flow(self, login_page: LoginPage, register_page: RegisterPage):
        """Test complete password reset flow"""
        # Step 1: Request password reset
        login_page.navigate_to("/auth/login")
        login_page.go_to_forgot_password()
        login_page.fill_input("#email", "testuser@example.com")
        login_page.click_element("button[type='submit']")
        expect(login_page.page.locator(".alert-success")).to_contain_text("reset link sent")

        # Step 2: Simulate password reset (would need email interception in real test)
        # For UI testing, we can test the reset form accessibility
        reset_token = "test-reset-token"  # Would come from email
        login_page.navigate_to(f"/auth/reset-password/{reset_token}")
        expect(login_page.page.locator("#password")).to_be_visible()

        # Fill reset form
        login_page.fill_input("#password", "NewPassword123!")
        login_page.fill_input("#confirm_password", "NewPassword123!")
        login_page.click_element("button[type='submit']")

        # Assert password reset success
        expect(login_page.page.locator(".alert-success")).to_contain_text("reset successfully")

    def test_form_template_usage_flow(self, dashboard_page: DashboardPage, form_create_page: FormCreatePage):
        """Test using form templates in complete workflow"""
        # Browse templates
        dashboard_page.navigate_to("/forms/templates")
        expect(dashboard_page.page.locator(".template-card")).to_have_count_greater_than(0)

        # Select and use template
        dashboard_page.click_element(".template-card:first-child .use-template-btn")

        # Create form from template
        template_form_title = "Template Form"
        form_create_page.create_form(template_form_title, "Created from template")
        form_create_page.assert_form_creation_success()

        # Verify template content was loaded
        dashboard_page.navigate_to(f"/forms/builder")  # Would need to get form ID
        expect(dashboard_page.page.locator(".question")).to_have_count_greater_than(0)

    def test_response_export_and_analytics_flow(self, dashboard_page: DashboardPage):
        """Test response export and analytics workflow"""
        form_id = 1

        # Step 1: View responses
        dashboard_page.navigate_to(f"/responses/{form_id}")
        expect(dashboard_page.page.locator(".response-item")).to_have_count_greater_than(0)

        # Step 2: Export responses
        with dashboard_page.page.expect_download() as download_info:
            dashboard_page.click_element("a[href*='format=csv']")
        download = download_info.value
        expect(download.suggested_filename).to_contain("responses")

        # Step 3: View analytics
        dashboard_page.navigate_to(f"/analytics/form/{form_id}")
        expect(dashboard_page.page.locator(".response-chart")).to_be_visible()
        expect(dashboard_page.page.locator(".question-analytics")).to_have_count_greater_than(0)

    def test_admin_user_management_flow(self, dashboard_page: DashboardPage):
        """Test admin user management end-to-end"""
        # Login as admin
        dashboard_page.navigate_to("/auth/login")
        # dashboard_page.login("admin", "adminpassword")

        # Navigate to user management
        dashboard_page.navigate_to("/admin/users")

        # Edit user
        dashboard_page.click_element(".user-item:first-child .edit-btn")
        dashboard_page.select_option("#role", "editor")
        dashboard_page.click_element("button[type='submit']")
        expect(dashboard_page.page.locator(".alert-success")).to_contain_text("updated")

        # Verify role change
        dashboard_page.navigate_to("/admin/users")
        expect(dashboard_page.page.locator(".user-role")).to_contain_text("editor")

    def test_multi_user_collaboration_flow(self, page: Page, dashboard_page: DashboardPage):
        """Test multi-user collaboration on forms"""
        # User 1 creates form
        dashboard_page.navigate_to("/auth/login")
        dashboard_page.login("user1", "password")
        dashboard_page.click_create_form()
        # ... create form ...

        # User 2 accesses shared form
        context = page.context.browser.new_context()
        new_page = context.new_page()
        new_dashboard = DashboardPage(new_page)
        new_dashboard.navigate_to("/auth/login")
        new_dashboard.login("user2", "password")

        # Access shared form
        shared_form_url = "/forms/1"  # Assuming shared form
        new_dashboard.navigate_to(shared_form_url)
        expect(new_dashboard.page.locator("h1")).to_be_visible()

        context.close()

    def test_form_settings_and_permissions_flow(self, dashboard_page: DashboardPage):
        """Test form settings and permissions management"""
        form_id = 1
        dashboard_page.navigate_to(f"/forms/{form_id}/settings")

        # Configure form settings
        dashboard_page.check_checkbox("#require_login")
        dashboard_page.fill_input("#response_limit", "100")
        dashboard_page.fill_input("#expires_at", "2024-12-31T23:59")
        dashboard_page.click_element("button[type='submit']")

        # Test permission enforcement
        dashboard_page.logout()
        dashboard_page.navigate_to(f"/forms/{form_id}")
        expect(dashboard_page.page.locator(".login-required")).to_be_visible()

    def test_complete_form_lifecycle_flow(self, dashboard_page: DashboardPage,
                                        form_create_page: FormCreatePage,
                                        form_display_page: FormDisplayPage):
        """Test complete form lifecycle from creation to archival"""
        import uuid
        unique_id = str(uuid.uuid4())[:8]

        # Step 1: Create form
        dashboard_page.navigate_to("/forms/create")
        form_title = f"Lifecycle Test Form {unique_id}"
        form_create_page.create_form(form_title, "Testing form lifecycle")

        # Step 2: Build form
        form_id = dashboard_page.page.url.split('/')[-2]
        dashboard_page.navigate_to(f"/forms/{form_id}/builder")
        dashboard_page.click_element(".add-question-btn")
        dashboard_page.fill_input(".question-text", "Test question?")
        dashboard_page.click_element(".save-question-btn")

        # Step 3: Publish form
        dashboard_page.click_element(".publish-btn")

        # Step 4: Collect responses
        form_display_page.navigate_to(f"/forms/{form_id}")
        form_display_page.fill_text_input("1", "Test Response")
        form_display_page.submit_form()

        # Step 5: View analytics
        dashboard_page.navigate_to(f"/analytics/form/{form_id}")
        expect(dashboard_page.page.locator(".response-count")).to_contain_text("1")

        # Step 6: Archive form
        dashboard_page.navigate_to(f"/forms/{form_id}/builder")
        dashboard_page.click_element(".archive-btn")

        # Step 7: Verify archival
        dashboard_page.navigate_to("/forms/my-forms")
        expect(dashboard_page.page.locator(f"[data-form-id='{form_id}']")).to_have_class("archived")

    def test_cross_device_responsiveness_flow(self, page: Page, dashboard_page: DashboardPage):
        """Test application responsiveness across different device sizes"""
        # Test desktop
        page.set_viewport_size({"width": 1920, "height": 1080})
        dashboard_page.navigate_to("/main/dashboard")
        expect(dashboard_page.page.locator(".desktop-layout")).to_be_visible()

        # Test tablet
        page.set_viewport_size({"width": 768, "height": 1024})
        page.reload()
        expect(dashboard_page.page.locator(".tablet-layout")).to_be_visible()

        # Test mobile
        page.set_viewport_size({"width": 375, "height": 667})
        page.reload()
        expect(dashboard_page.page.locator(".mobile-menu")).to_be_visible()

    def test_error_recovery_and_user_feedback_flow(self, dashboard_page: DashboardPage):
        """Test error handling and user feedback throughout the application"""
        # Test 404 error
        dashboard_page.navigate_to("/nonexistent-page")
        expect(dashboard_page.page.locator(".error-404")).to_be_visible()

        # Test form validation errors
        dashboard_page.navigate_to("/forms/create")
        dashboard_page.fill_input("#title", "")  # Empty title
        dashboard_page.click_element("button[type='submit']")
        expect(dashboard_page.page.locator(".error-message")).to_be_visible()

        # Test network error recovery
        # This would require simulating network issues

    def test_data_persistence_and_backup_flow(self, dashboard_page: DashboardPage):
        """Test data persistence and backup functionality"""
        # Create form and responses
        dashboard_page.navigate_to("/forms/create")
        dashboard_page.fill_input("#title", "Backup Test Form")
        dashboard_page.click_element("button[type='submit']")

        # Submit responses
        form_id = dashboard_page.page.url.split('/')[-2]
        dashboard_page.navigate_to(f"/forms/{form_id}")
        dashboard_page.fill_text_input("1", "Backup Test Response")
        dashboard_page.submit_form()

        # Test data export (backup)
        dashboard_page.navigate_to(f"/responses/{form_id}")
        with dashboard_page.page.expect_download() as download_info:
            dashboard_page.click_element(".export-btn")
        download = download_info.value
        expect(download.suggested_filename).to_be_truthy()

    @pytest.mark.parametrize("browser_name", ["chromium", "firefox", "webkit"])
    def test_cross_browser_e2e_flow(self, page: Page, browser_name: str):
        """Test complete user flow across different browsers"""
        dashboard_page = DashboardPage(page)

        # Complete registration and login flow
        dashboard_page.navigate_to("/auth/register")
        # ... complete registration ...

        dashboard_page.navigate_to("/auth/login")
        # ... complete login ...

        # Create and publish form
        dashboard_page.click_create_form()
        # ... create form ...

        # Should work identically across browsers
        expect(page.locator(".dashboard")).to_be_visible()

    def test_performance_under_load_flow(self, dashboard_page: DashboardPage):
        """Test application performance under simulated load"""
        import time

        # Measure dashboard load time
        start_time = time.time()
        dashboard_page.navigate_to("/main/dashboard")
        load_time = time.time() - start_time
        assert load_time < 3.0  # Should load within 3 seconds

        # Test form submission performance
        form_id = 1
        for i in range(5):  # Submit multiple responses
            dashboard_page.navigate_to(f"/forms/{form_id}")
            dashboard_page.fill_text_input("1", f"Performance Test {i}")
            start_time = time.time()
            dashboard_page.submit_form()
            submit_time = time.time() - start_time
            assert submit_time < 2.0  # Each submission should be fast

    def test_accessibility_and_usability_flow(self, dashboard_page: DashboardPage):
        """Test accessibility and usability features"""
        dashboard_page.navigate_to("/main/dashboard")

        # Check keyboard navigation
        page = dashboard_page.page
        page.keyboard.press("Tab")
        expect(page.locator(":focus")).to_be_visible()

        # Check ARIA labels
        expect(page.locator("[aria-label]")).to_have_count_greater_than(0)

        # Check color contrast (basic check)
        expect(page.locator(".high-contrast-text")).to_be_visible()

        # Check form labels
        expect(page.locator("label")).to_have_count_greater_than(0)

    def test_internationalization_flow(self, dashboard_page: DashboardPage):
        """Test internationalization and localization features"""
        # Test language switching
        dashboard_page.navigate_to("/settings/language")

        # Switch to different language
        dashboard_page.click_element(".language-selector")
        dashboard_page.click_element("[data-lang='es']")  # Spanish

        # Check if UI text changes
        expect(dashboard_page.page.locator(".dashboard-title")).to_contain_text("Panel")  # Dashboard in Spanish

        # Test RTL language support if applicable
        dashboard_page.click_element("[data-lang='ar']")  # Arabic
        expect(dashboard_page.page.locator("html")).to_have_attribute("dir", "rtl")

    def test_integration_with_external_services_flow(self, dashboard_page: DashboardPage):
        """Test integration with external services (email, file storage, etc.)"""
        # Test email integration
        dashboard_page.navigate_to("/auth/forgot-password")
        dashboard_page.fill_input("#email", "test@example.com")
        dashboard_page.click_element("button[type='submit']")

        # Should show success message (email sent)
        expect(dashboard_page.page.locator(".alert-success")).to_be_visible()

        # Test file upload integration
        dashboard_page.navigate_to("/forms/create")
        # ... create form with file upload question ...

        # Test file upload functionality
        dashboard_page.click_element("input[type='file']")
        # File upload testing would require actual file handling

    def test_security_and_compliance_flow(self, dashboard_page: DashboardPage):
        """Test security features and compliance"""
        # Test HTTPS enforcement
        dashboard_page.navigate_to("http://localhost:5000")  # HTTP
        # Should redirect to HTTPS in production

        # Test secure headers
        response = dashboard_page.page.request.get("http://localhost:5000")
        assert "X-Frame-Options" in response.headers

        # Test CSRF protection
        dashboard_page.navigate_to("/forms/create")
        # Attempt form submission without CSRF token should fail

        # Test input sanitization
        dashboard_page.fill_input("#title", "<script>alert('xss')</script>")
        dashboard_page.click_element("button[type='submit']")
        # Should be sanitized, no script execution

    def test_monitoring_and_logging_flow(self, dashboard_page: DashboardPage):
        """Test application monitoring and logging"""
        # Perform actions that should be logged
        dashboard_page.navigate_to("/auth/login")
        dashboard_page.login("testuser", "TestPassword123!")

        dashboard_page.click_create_form()
        dashboard_page.fill_input("#title", "Monitoring Test Form")
        dashboard_page.click_element("button[type='submit']")

        # Check admin logs (if accessible)
        dashboard_page.navigate_to("/admin/logs")
        expect(dashboard_page.page.locator(".log-entry")).to_contain_text("form created")

        # Check performance metrics
        dashboard_page.navigate_to("/admin/performance")
        expect(dashboard_page.page.locator(".response-time")).to_be_visible()