from .base_page import BasePage


class LoginPage(BasePage):
    """Page object for the login page"""

    def __init__(self, page):
        super().__init__(page)
        self.username_input = "#username"
        self.password_input = "#password"
        self.login_button = "button[type='submit']"
        self.register_link = "a[href*='register']"
        self.forgot_password_link = "a[href*='forgot-password']"
        self.error_message = ".alert-danger, .text-red-500"
        self.success_message = ".alert-success, .text-green-500"

    def login(self, username: str, password: str):
        """Perform login with given credentials"""
        self.fill_input(self.username_input, username)
        self.fill_input(self.password_input, password)
        self.click_element(self.login_button)
        self.wait_for_load()

    def go_to_register(self):
        """Navigate to registration page"""
        self.click_element(self.register_link)

    def go_to_forgot_password(self):
        """Navigate to forgot password page"""
        self.click_element(self.forgot_password_link)

    def get_error_message(self):
        """Get error message text"""
        return self.get_text(self.error_message)

    def get_success_message(self):
        """Get success message text"""
        return self.get_text(self.success_message)

    def is_login_form_visible(self):
        """Check if login form is visible"""
        return self.is_visible(self.username_input) and self.is_visible(self.password_input)

    def assert_login_success(self):
        """Assert that login was successful by checking URL or dashboard elements"""
        # Check if redirected to dashboard or main page
        self.expect_url_contains("/dashboard|/main")

    def assert_login_failed(self, expected_error: str = None):
        """Assert that login failed"""
        if expected_error:
            self.expect_text(self.error_message, expected_error)
        else:
            self.expect_visible(self.error_message)