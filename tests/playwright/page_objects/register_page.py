from .base_page import BasePage


class RegisterPage(BasePage):
    """Page object for the registration page"""

    def __init__(self, page):
        super().__init__(page)
        self.first_name_input = "#first_name"
        self.last_name_input = "#last_name"
        self.username_input = "#username"
        self.email_input = "#email"
        self.password_input = "#password"
        self.register_button = "button[type='submit']"
        self.login_link = "a[href*='login']"
        self.error_message = ".alert-danger, .text-red-500"
        self.success_message = ".alert-success, .text-green-500"

    def register(self, first_name: str = "", last_name: str = "", username: str = "", email: str = "", password: str = ""):
        """Perform registration with given details"""
        if first_name:
            self.fill_input(self.first_name_input, first_name)
        if last_name:
            self.fill_input(self.last_name_input, last_name)
        self.fill_input(self.username_input, username)
        self.fill_input(self.email_input, email)
        self.fill_input(self.password_input, password)
        self.click_element(self.register_button)
        self.wait_for_load()

    def go_to_login(self):
        """Navigate to login page"""
        self.click_element(self.login_link)

    def get_error_message(self):
        """Get error message text"""
        return self.get_text(self.error_message)

    def get_success_message(self):
        """Get success message text"""
        return self.get_text(self.success_message)

    def is_registration_form_visible(self):
        """Check if registration form is visible"""
        return self.is_visible(self.username_input) and self.is_visible(self.email_input) and self.is_visible(self.password_input)

    def assert_registration_success(self):
        """Assert that registration was successful"""
        # Check for success message about email verification
        self.expect_text(self.success_message, "Please check your email to verify your account")

    def assert_registration_failed(self, expected_error: str = None):
        """Assert that registration failed"""
        if expected_error:
            self.expect_text(self.error_message, expected_error)
        else:
            self.expect_visible(self.error_message)

    def assert_validation_error(self, field: str, message: str):
        """Assert validation error for specific field"""
        # Look for field-specific error messages
        error_selector = f"[data-field='{field}'] .error, #{field} ~ .error, .text-red-500"
        self.expect_text(error_selector, message)