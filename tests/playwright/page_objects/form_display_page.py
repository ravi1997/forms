from .base_page import BasePage


class FormDisplayPage(BasePage):
    """Page object for form display/submission page"""

    def __init__(self, page):
        super().__init__(page)
        self.form_title = "h1"
        self.form_description = ".form-description, p.text-gray-600"
        self.submit_button = "button[type='submit']"
        self.success_message = ".alert-success, .text-green-500"
        self.error_message = ".alert-danger, .text-red-500"

    def fill_text_input(self, question_id: str, value: str):
        """Fill a text input field"""
        selector = f"input#question_{question_id}"
        self.fill_input(selector, value)

    def fill_textarea(self, question_id: str, value: str):
        """Fill a textarea field"""
        selector = f"textarea#question_{question_id}"
        self.fill_input(selector, value)

    def select_radio_option(self, question_id: str, value: str):
        """Select a radio button option"""
        selector = f"input[type='radio'][name='question_{question_id}'][value='{value}']"
        self.click_element(selector)

    def select_checkbox_option(self, question_id: str, value: str):
        """Select a checkbox option"""
        selector = f"input[type='checkbox'][name='question_{question_id}'][value='{value}']"
        self.click_element(selector)

    def select_dropdown_option(self, question_id: str, value: str):
        """Select a dropdown option"""
        selector = f"select#question_{question_id}"
        self.page.select_option(selector, value)

    def fill_email_input(self, question_id: str, email: str):
        """Fill an email input field"""
        selector = f"input[type='email']#question_{question_id}"
        self.fill_input(selector, email)

    def fill_number_input(self, question_id: str, number: str):
        """Fill a number input field"""
        selector = f"input[type='number']#question_{question_id}"
        self.fill_input(selector, number)

    def fill_date_input(self, question_id: str, date: str):
        """Fill a date input field"""
        selector = f"input[type='date']#question_{question_id}"
        self.fill_input(selector, date)

    def upload_file(self, question_id: str, file_path: str):
        """Upload a file"""
        selector = f"input[type='file']#question_{question_id}"
        self.page.set_input_files(selector, file_path)

    def submit_form(self):
        """Submit the form"""
        self.click_element(self.submit_button)
        self.wait_for_load()

    def get_form_title(self):
        """Get the form title"""
        return self.get_text(self.form_title)

    def get_success_message(self):
        """Get success message after submission"""
        return self.get_text(self.success_message)

    def get_error_message(self):
        """Get error message"""
        return self.get_text(self.error_message)

    def is_form_visible(self):
        """Check if form is visible"""
        return self.is_visible(self.form_title) and self.is_visible(self.submit_button)

    def assert_form_submission_success(self):
        """Assert that form was submitted successfully"""
        self.expect_text(self.success_message, "submitted successfully")

    def assert_validation_error(self, expected_error: str):
        """Assert validation error"""
        self.expect_text(self.error_message, expected_error)

    def assert_required_field_error(self, question_text: str):
        """Assert required field error"""
        error_text = f"Required question not answered: {question_text}"
        self.expect_text(self.error_message, error_text)