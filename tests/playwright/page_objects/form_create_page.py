from .base_page import BasePage


class FormCreatePage(BasePage):
    """Page object for form creation page"""

    def __init__(self, page):
        super().__init__(page)
        self.title_input = "#title"
        self.description_input = "#description"
        self.create_button = "button[type='submit']"
        self.cancel_button = ".cancel-btn, a[href*='dashboard']"
        self.browse_templates_button = "a[href*='templates']"
        self.error_message = ".alert-danger, .text-red-500"
        self.success_message = ".alert-success, .text-green-500"

    def create_form(self, title: str, description: str = ""):
        """Create a new form with given title and description"""
        self.fill_input(self.title_input, title)
        if description:
            self.fill_input(self.description_input, description)
        self.click_element(self.create_button)
        self.wait_for_load()

    def cancel_creation(self):
        """Cancel form creation"""
        self.click_element(self.cancel_button)

    def browse_templates(self):
        """Navigate to templates page"""
        self.click_element(self.browse_templates_button)

    def get_error_message(self):
        """Get error message text"""
        return self.get_text(self.error_message)

    def is_form_creation_visible(self):
        """Check if form creation form is visible"""
        return self.is_visible(self.title_input) and self.is_visible(self.create_button)

    def assert_form_creation_success(self):
        """Assert that form was created successfully"""
        # Should redirect to form builder
        self.expect_url_contains("/builder")

    def assert_validation_error(self, expected_error: str):
        """Assert validation error"""
        self.expect_text(self.error_message, expected_error)

    def assert_required_field_error(self):
        """Assert that title is required"""
        self.expect_text(self.error_message, "Form title is required")