from .base_page import BasePage


class DashboardPage(BasePage):
    """Page object for the main dashboard"""

    def __init__(self, page):
        super().__init__(page)
        self.welcome_message = "h1, .dashboard-title"
        self.create_form_button = "a[href*='create'], button[onclick*='create']"
        self.my_forms_link = "a[href*='my-forms']"
        self.analytics_link = "a[href*='analytics']"
        self.profile_link = "a[href*='profile']"
        self.logout_link = "a[href*='logout']"
        self.forms_list = ".forms-list, .card, [data-testid='form-card']"
        self.total_forms_count = ".stats .forms-count, [data-testid='total-forms']"
        self.total_responses_count = ".stats .responses-count, [data-testid='total-responses']"

    def is_dashboard_loaded(self):
        """Check if dashboard is properly loaded"""
        return self.is_visible(self.welcome_message) or "dashboard" in self.get_current_url().lower()

    def click_create_form(self):
        """Click create new form button"""
        self.click_element(self.create_form_button)

    def go_to_my_forms(self):
        """Navigate to my forms page"""
        self.click_element(self.my_forms_link)

    def go_to_analytics(self):
        """Navigate to analytics page"""
        self.click_element(self.analytics_link)

    def go_to_profile(self):
        """Navigate to profile page"""
        self.click_element(self.profile_link)

    def logout(self):
        """Perform logout"""
        self.click_element(self.logout_link)
        self.wait_for_load()

    def get_forms_count(self):
        """Get total forms count from dashboard"""
        if self.is_visible(self.total_forms_count):
            return int(self.get_text(self.total_forms_count).strip())
        return 0

    def get_responses_count(self):
        """Get total responses count from dashboard"""
        if self.is_visible(self.total_responses_count):
            return int(self.get_text(self.total_responses_count).strip())
        return 0

    def get_recent_forms(self):
        """Get list of recent forms displayed on dashboard"""
        forms = []
        form_elements = self.page.query_selector_all(self.forms_list)
        for form in form_elements:
            title = form.query_selector("h3, .form-title")
            if title:
                forms.append(title.text_content().strip())
        return forms

    def assert_dashboard_accessible(self):
        """Assert that dashboard is accessible and shows expected elements"""
        self.expect_visible(self.welcome_message)
        self.expect_visible(self.create_form_button)

    def assert_user_logged_in(self, username: str = None):
        """Assert that user is logged in"""
        # Check for logout link or user menu
        self.expect_visible(self.logout_link)
        if username:
            # Look for username in header or navigation
            self.expect_text(".user-menu, .navbar-user", username)