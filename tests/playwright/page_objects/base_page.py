from playwright.sync_api import Page, expect


class BasePage:
    """Base page object with common functionality"""

    def __init__(self, page: Page):
        self.page = page
        self.base_url = "http://localhost:5000"

    def navigate_to(self, path: str = ""):
        """Navigate to a specific path"""
        self.page.goto(f"{self.base_url}{path}")

    def wait_for_load(self):
        """Wait for page to load"""
        self.page.wait_for_load_state("networkidle")

    def get_current_url(self):
        """Get current page URL"""
        return self.page.url

    def get_title(self):
        """Get page title"""
        return self.page.title()

    def click_element(self, selector: str):
        """Click an element by selector"""
        self.page.click(selector)

    def fill_input(self, selector: str, value: str):
        """Fill an input field"""
        self.page.fill(selector, value)

    def get_text(self, selector: str):
        """Get text content of an element"""
        return self.page.text_content(selector)

    def is_visible(self, selector: str):
        """Check if element is visible"""
        return self.page.is_visible(selector)

    def wait_for_selector(self, selector: str, timeout: int = 10000):
        """Wait for selector to appear"""
        self.page.wait_for_selector(selector, timeout=timeout)

    def expect_text(self, selector: str, expected_text: str):
        """Assert that element contains expected text"""
        expect(self.page.locator(selector)).to_contain_text(expected_text)

    def expect_visible(self, selector: str):
        """Assert that element is visible"""
        expect(self.page.locator(selector)).to_be_visible()

    def expect_not_visible(self, selector: str):
        """Assert that element is not visible"""
        expect(self.page.locator(selector)).to_be_hidden()

    def expect_url_contains(self, text: str):
        """Assert that URL contains specific text"""
        expect(self.page).to_have_url(re.compile(text))

    def take_screenshot(self, name: str):
        """Take a screenshot for debugging"""
        self.page.screenshot(path=f"screenshots/{name}.png")

    def handle_alert(self, accept: bool = True):
        """Handle browser alert dialogs"""
        if accept:
            self.page.on("dialog", lambda dialog: dialog.accept())
        else:
            self.page.on("dialog", lambda dialog: dialog.dismiss())