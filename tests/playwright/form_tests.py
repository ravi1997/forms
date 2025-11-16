import pytest
from playwright.sync_api import Page, expect
from page_objects.dashboard_page import DashboardPage
from page_objects.form_create_page import FormCreatePage
from page_objects.form_display_page import FormDisplayPage


@pytest.fixture
def dashboard_page(page: Page):
    return DashboardPage(page)


@pytest.fixture
def form_create_page(page: Page):
    return FormCreatePage(page)


@pytest.fixture
def form_display_page(page: Page):
    return FormDisplayPage(page)


class TestFormManagement:
    """Test form creation, editing, publishing, and management functionality"""

    def test_successful_form_creation(self, dashboard_page: DashboardPage, form_create_page: FormCreatePage):
        """Test creating a new form successfully"""
        # Login and navigate to dashboard
        dashboard_page.navigate_to("/auth/login")
        # Assuming login is handled in conftest or separate setup

        # Click create form button
        dashboard_page.click_create_form()

        # Fill form creation details
        import uuid
        form_title = f"Test Form {str(uuid.uuid4())[:8]}"
        form_description = "This is a test form for automated testing"

        form_create_page.create_form(form_title, form_description)

        # Assert form creation success
        form_create_page.assert_form_creation_success()

        # Verify form appears in dashboard
        dashboard_page.navigate_to("/main/dashboard")
        expect(dashboard_page.page.locator(".forms-list")).to_contain_text(form_title)

    def test_form_creation_validation(self, form_create_page: FormCreatePage):
        """Test form creation validation errors"""
        form_create_page.navigate_to("/forms/create")

        # Test empty title
        form_create_page.create_form("", "Description")
        form_create_page.assert_required_field_error()

        # Test title too long (if validation exists)
        long_title = "A" * 300
        form_create_page.create_form(long_title, "Description")
        # Assert appropriate error message

    def test_form_publishing_workflow(self, dashboard_page: DashboardPage):
        """Test publishing a form and making it publicly accessible"""
        # Navigate to form builder (assuming form exists)
        form_id = 1  # Would be dynamic in real test
        dashboard_page.navigate_to(f"/forms/{form_id}/builder")

        # Publish the form
        dashboard_page.click_element(".publish-btn, button[onclick*='publish']")

        # Assert success message
        expect(dashboard_page.page.locator(".alert-success")).to_contain_text("published successfully")

        # Verify form is accessible publicly
        dashboard_page.navigate_to(f"/forms/{form_id}")
        expect(dashboard_page.page.locator("h1")).to_be_visible()

    def test_form_unpublishing(self, dashboard_page: DashboardPage):
        """Test unpublishing a form"""
        form_id = 1
        dashboard_page.navigate_to(f"/forms/{form_id}/builder")

        # Unpublish the form
        dashboard_page.click_element(".unpublish-btn, button[onclick*='unpublish']")

        # Assert success
        expect(dashboard_page.page.locator(".alert-success")).to_contain_text("unpublished successfully")

        # Verify form is not accessible publicly
        dashboard_page.navigate_to(f"/forms/{form_id}")
        expect(dashboard_page.page.locator(".form-not-available")).to_be_visible()

    def test_form_editing(self, dashboard_page: DashboardPage):
        """Test editing form metadata"""
        form_id = 1
        dashboard_page.navigate_to(f"/forms/{form_id}/edit")

        # Update form details
        new_title = "Updated Test Form"
        new_description = "Updated description"

        dashboard_page.fill_input("#title", new_title)
        dashboard_page.fill_input("#description", new_description)
        dashboard_page.click_element("button[type='submit']")

        # Assert success
        expect(dashboard_page.page.locator(".alert-success")).to_contain_text("updated successfully")

        # Verify changes
        dashboard_page.navigate_to(f"/forms/{form_id}/edit")
        expect(dashboard_page.page.locator("#title")).to_have_value(new_title)
        expect(dashboard_page.page.locator("#description")).to_have_value(new_description)

    def test_form_deletion(self, dashboard_page: DashboardPage):
        """Test deleting a form"""
        form_id = 1
        dashboard_page.navigate_to(f"/forms/{form_id}/edit")

        # Delete form
        dashboard_page.click_element(".delete-btn, button[onclick*='delete']")

        # Confirm deletion (if modal appears)
        dashboard_page.page.locator(".confirm-delete").click()

        # Assert success
        expect(dashboard_page.page.locator(".alert-success")).to_contain_text("deleted successfully")

        # Verify form no longer exists
        dashboard_page.navigate_to(f"/forms/{form_id}")
        expect(dashboard_page.page).to_have_url("**/forms/form_not_available")

    def test_form_settings_management(self, dashboard_page: DashboardPage):
        """Test form settings configuration"""
        form_id = 1
        dashboard_page.navigate_to(f"/forms/{form_id}/settings")

        # Configure settings
        dashboard_page.check_checkbox("#require_login")
        dashboard_page.check_checkbox("#collect_ip")
        dashboard_page.fill_input("#response_limit", "100")
        dashboard_page.fill_input("#expires_at", "2024-12-31T23:59")

        dashboard_page.click_element("button[type='submit']")

        # Assert success
        expect(dashboard_page.page.locator(".alert-success")).to_contain_text("settings updated")

    def test_form_archiving_and_restoration(self, dashboard_page: DashboardPage):
        """Test archiving and restoring forms"""
        form_id = 1

        # Archive form
        dashboard_page.navigate_to(f"/forms/{form_id}/builder")
        dashboard_page.click_element(".archive-btn")
        expect(dashboard_page.page.locator(".alert-success")).to_contain_text("archived successfully")

        # Verify archived status
        dashboard_page.navigate_to("/forms/my-forms")
        expect(dashboard_page.page.locator(f"[data-form-id='{form_id}']")).to_have_class("archived")

        # Restore form
        dashboard_page.click_element(f"[data-form-id='{form_id}'] .restore-btn")
        expect(dashboard_page.page.locator(".alert-success")).to_contain_text("restored successfully")

    def test_question_library_management(self, dashboard_page: DashboardPage):
        """Test question library functionality"""
        dashboard_page.navigate_to("/forms/question_library")

        # Add new question
        dashboard_page.click_element(".add-question-btn")
        dashboard_page.fill_input("#question_text", "What is your favorite color?")
        dashboard_page.select_option("#question_type", "multiple_choice")
        dashboard_page.fill_input("#options", "Red\nBlue\nGreen")
        dashboard_page.click_element("button[type='submit']")

        # Assert question added
        expect(dashboard_page.page.locator(".question-list")).to_contain_text("What is your favorite color?")

        # Edit question
        dashboard_page.click_element(".edit-question-btn")
        dashboard_page.fill_input("#question_text", "What is your favorite color? (Updated)")
        dashboard_page.click_element("button[type='submit']")

        # Assert updated
        expect(dashboard_page.page.locator(".question-list")).to_contain_text("(Updated)")

    def test_form_templates_usage(self, dashboard_page: DashboardPage, form_create_page: FormCreatePage):
        """Test using form templates"""
        # Browse templates
        dashboard_page.navigate_to("/forms/templates")

        # Select a template
        dashboard_page.click_element(".template-card:first-child .use-template-btn")

        # Create form from template
        form_create_page.create_form("Template Form", "Created from template")

        # Assert form created with template content
        form_create_page.assert_form_creation_success()

    def test_form_builder_functionality(self, dashboard_page: DashboardPage):
        """Test form builder interface"""
        form_id = 1
        dashboard_page.navigate_to(f"/forms/{form_id}/builder")

        # Add a section
        dashboard_page.click_element(".add-section-btn")
        dashboard_page.fill_input(".section-title", "Personal Information")
        dashboard_page.fill_input(".section-description", "Please provide your personal details")

        # Add questions to section
        dashboard_page.click_element(".add-question-btn")
        dashboard_page.fill_input(".question-text", "What is your name?")
        dashboard_page.select_option(".question-type", "text")
        dashboard_page.check_checkbox(".question-required")

        # Save structure
        dashboard_page.click_element(".save-structure-btn")

        # Assert success
        expect(dashboard_page.page.locator(".alert-success")).to_contain_text("structure updated")

    def test_form_preview_functionality(self, dashboard_page: DashboardPage):
        """Test form preview before publishing"""
        form_id = 1
        dashboard_page.navigate_to(f"/forms/{form_id}/preview")

        # Verify preview shows form correctly
        expect(dashboard_page.page.locator("h1")).to_be_visible()
        expect(dashboard_page.page.locator(".question")).to_have_count_greater_than(0)

        # Test preview submission (should not actually submit)
        dashboard_page.fill_input("input[type='text']", "Test Answer")
        dashboard_page.click_element("button[type='submit']")

        # Assert preview mode prevents actual submission
        expect(dashboard_page.page).to_have_url(re.compile(r"/forms/\d+/preview"))

    def test_bulk_form_operations(self, dashboard_page: DashboardPage):
        """Test bulk operations on forms"""
        dashboard_page.navigate_to("/forms/my-forms")

        # Select multiple forms
        dashboard_page.check_checkbox(".form-checkbox")
        dashboard_page.click_element(".bulk-actions-btn")

        # Test bulk publish
        dashboard_page.click_element(".bulk-publish")
        expect(dashboard_page.page.locator(".alert-success")).to_contain_text("forms published")

        # Test bulk archive
        dashboard_page.check_checkbox(".form-checkbox")
        dashboard_page.click_element(".bulk-archive")
        expect(dashboard_page.page.locator(".alert-success")).to_contain_text("forms archived")

    def test_form_search_and_filtering(self, dashboard_page: DashboardPage):
        """Test searching and filtering forms"""
        dashboard_page.navigate_to("/forms/my-forms")

        # Search by title
        dashboard_page.fill_input(".search-input", "Test Form")
        dashboard_page.click_element(".search-btn")

        # Assert results filtered
        form_cards = dashboard_page.page.locator(".form-card")
        expect(form_cards).to_have_count_greater_than(0)
        expect(form_cards.first).to_contain_text("Test Form")

        # Filter by status
        dashboard_page.select_option(".status-filter", "published")
        expect(dashboard_page.page.locator(".form-card.published")).to_be_visible()
        expect(dashboard_page.page.locator(".form-card.draft")).to_be_hidden()

    def test_form_permissions_and_sharing(self, dashboard_page: DashboardPage):
        """Test form sharing and permission management"""
        form_id = 1
        dashboard_page.navigate_to(f"/forms/{form_id}/settings")

        # Set form to private
        dashboard_page.check_checkbox("#require_login")

        # Generate share link
        dashboard_page.click_element(".generate-share-link")
        expect(dashboard_page.page.locator(".share-link")).to_be_visible()

        # Copy share link
        share_link = dashboard_page.get_text(".share-link input")

        # Test access without login (should fail)
        dashboard_page.navigate_to(share_link)
        expect(dashboard_page.page).to_have_url("**/auth/login")

    @pytest.mark.parametrize("question_type", ["text", "multiple_choice", "checkbox", "rating", "file_upload"])
    def test_different_question_types_in_builder(self, dashboard_page: DashboardPage, question_type: str):
        """Test adding different question types in form builder"""
        form_id = 1
        dashboard_page.navigate_to(f"/forms/{form_id}/builder")

        # Add question of specific type
        dashboard_page.click_element(".add-question-btn")
        dashboard_page.select_option(".question-type", question_type)
        dashboard_page.fill_input(".question-text", f"Test {question_type} question")

        if question_type in ["multiple_choice", "checkbox"]:
            dashboard_page.fill_input(".question-options", "Option 1\nOption 2\nOption 3")

        dashboard_page.click_element(".save-question-btn")

        # Assert question added with correct type
        expect(dashboard_page.page.locator(f".question[data-type='{question_type}']")).to_be_visible()

    def test_form_response_limits(self, dashboard_page: DashboardPage, form_display_page: FormDisplayPage):
        """Test form response limits"""
        form_id = 1

        # Set response limit
        dashboard_page.navigate_to(f"/forms/{form_id}/settings")
        dashboard_page.fill_input("#response_limit", "1")
        dashboard_page.click_element("button[type='submit']")

        # Submit first response
        form_display_page.navigate_to(f"/forms/{form_id}")
        form_display_page.fill_text_input("1", "Test Answer")
        form_display_page.submit_form()
        form_display_page.assert_form_submission_success()

        # Try to submit second response (should fail)
        form_display_page.navigate_to(f"/forms/{form_id}")
        form_display_page.fill_text_input("1", "Another Answer")
        form_display_page.submit_form()
        expect(form_display_page.page.locator(".error")).to_contain_text("response limit reached")

    def test_form_expiration(self, dashboard_page: DashboardPage):
        """Test form expiration functionality"""
        form_id = 1

        # Set expiration date in the past
        dashboard_page.navigate_to(f"/forms/{form_id}/settings")
        dashboard_page.fill_input("#expires_at", "2020-01-01T00:00")
        dashboard_page.click_element("button[type='submit']")

        # Try to access expired form
        dashboard_page.navigate_to(f"/forms/{form_id}")
        expect(dashboard_page.page.locator(".form-expired")).to_be_visible()

    def test_form_analytics_integration(self, dashboard_page: DashboardPage):
        """Test form analytics integration"""
        form_id = 1
        dashboard_page.navigate_to(f"/analytics/form/{form_id}")

        # Assert analytics data loads
        expect(dashboard_page.page.locator(".analytics-chart")).to_be_visible()
        expect(dashboard_page.page.locator(".response-count")).to_be_visible()

        # Test different analytics views
        dashboard_page.click_element(".time-analytics-tab")
        expect(dashboard_page.page.locator(".time-chart")).to_be_visible()

        dashboard_page.click_element(".question-analytics-tab")
        expect(dashboard_page.page.locator(".question-breakdown")).to_be_visible()