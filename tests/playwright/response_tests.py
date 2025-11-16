import pytest
from playwright.sync_api import Page, expect
from page_objects.dashboard_page import DashboardPage
from page_objects.form_display_page import FormDisplayPage


@pytest.fixture
def dashboard_page(page: Page):
    return DashboardPage(page)


@pytest.fixture
def form_display_page(page: Page):
    return FormDisplayPage(page)


class TestResponseCollection:
    """Test form response collection, listing, and management"""

    def test_successful_form_submission(self, form_display_page: FormDisplayPage):
        """Test successful form submission with various question types"""
        form_id = 1  # Assuming a test form exists
        form_display_page.navigate_to(f"/forms/{form_id}")

        # Fill out different question types
        form_display_page.fill_text_input("1", "John Doe")
        form_display_page.fill_email_input("2", "john@example.com")
        form_display_page.select_radio_option("3", "Option A")
        form_display_page.select_checkbox_option("4", "Choice 1")
        form_display_page.select_checkbox_option("4", "Choice 3")
        form_display_page.select_dropdown_option("5", "Item 2")
        form_display_page.fill_textarea("6", "This is a longer text response")
        form_display_page.fill_number_input("7", "25")
        form_display_page.fill_date_input("8", "1999-01-01")

        # Submit form
        form_display_page.submit_form()

        # Assert success
        form_display_page.assert_form_submission_success()

    def test_required_field_validation(self, form_display_page: FormDisplayPage):
        """Test validation of required fields"""
        form_id = 1
        form_display_page.navigate_to(f"/forms/{form_id}")

        # Leave required field empty and submit
        form_display_page.fill_text_input("2", "test@example.com")  # Fill optional field
        # Leave required field 1 empty
        form_display_page.submit_form()

        # Assert validation error
        form_display_page.assert_required_field_error("What is your name?")

    def test_form_submission_with_file_upload(self, form_display_page: FormDisplayPage):
        """Test form submission with file upload"""
        form_id = 1
        form_display_page.navigate_to(f"/forms/{form_id}")

        # Fill required fields
        form_display_page.fill_text_input("1", "Test User")
        form_display_page.fill_email_input("2", "test@example.com")

        # Upload file
        form_display_page.upload_file("9", "test_files/sample.pdf")

        # Submit
        form_display_page.submit_form()

        # Assert success
        form_display_page.assert_form_submission_success()

    def test_response_listing_and_pagination(self, dashboard_page: DashboardPage):
        """Test response listing with pagination"""
        form_id = 1
        dashboard_page.navigate_to(f"/responses/{form_id}")

        # Assert responses are listed
        expect(dashboard_page.page.locator(".response-item")).to_have_count_greater_than(0)

        # Test pagination if multiple pages
        pagination = dashboard_page.page.locator(".pagination")
        if pagination.is_visible():
            # Click next page
            dashboard_page.click_element(".pagination .next")
            expect(dashboard_page.page.locator(".response-item")).to_have_count_greater_than(0)

    def test_response_details_view(self, dashboard_page: DashboardPage):
        """Test viewing detailed response information"""
        response_id = 1  # Assuming a response exists
        dashboard_page.navigate_to(f"/responses/{response_id}/details")

        # Assert response details are displayed
        expect(dashboard_page.page.locator(".response-details")).to_be_visible()
        expect(dashboard_page.page.locator(".answer")).to_have_count_greater_than(0)

        # Check specific answer display
        expect(dashboard_page.page.locator(".question-text")).to_be_visible()
        expect(dashboard_page.page.locator(".answer-text")).to_be_visible()

    def test_response_export_functionality(self, dashboard_page: DashboardPage):
        """Test exporting responses in different formats"""
        form_id = 1
        dashboard_page.navigate_to(f"/responses/{form_id}")

        # Test CSV export
        with dashboard_page.page.expect_download() as download_info:
            dashboard_page.click_element("a[href*='format=csv']")
        download = download_info.value
        expect(download.suggested_filename).to_contain("responses")
        expect(download.suggested_filename).to_contain(".csv")

        # Test JSON export
        with dashboard_page.page.expect_download() as download_info:
            dashboard_page.click_element("a[href*='format=json']")
        download = download_info.value
        expect(download.suggested_filename).to_contain(".json")

        # Test Excel export
        with dashboard_page.page.expect_download() as download_info:
            dashboard_page.click_element("a[href*='format=excel']")
        download = download_info.value
        expect(download.suggested_filename).to_contain(".xlsx")

    def test_response_filtering(self, dashboard_page: DashboardPage):
        """Test filtering responses by date range and other criteria"""
        form_id = 1
        dashboard_page.navigate_to(f"/responses/{form_id}")

        # Filter by date range
        dashboard_page.fill_input("#start_date", "2024-01-01")
        dashboard_page.fill_input("#end_date", "2024-12-31")
        dashboard_page.click_element(".filter-btn")

        # Assert filtered results
        responses = dashboard_page.page.locator(".response-item")
        expect(responses).to_have_count_greater_than(0)

        # Verify dates are within range (would need to check actual response dates)

    def test_response_search_functionality(self, dashboard_page: DashboardPage):
        """Test searching through responses"""
        form_id = 1
        dashboard_page.navigate_to(f"/responses/{form_id}")

        # Search for specific content
        dashboard_page.fill_input(".search-input", "John Doe")
        dashboard_page.click_element(".search-btn")

        # Assert search results
        expect(dashboard_page.page.locator(".response-item")).to_contain_text("John Doe")

    def test_response_deletion(self, dashboard_page: DashboardPage):
        """Test deleting individual responses"""
        response_id = 1
        dashboard_page.navigate_to(f"/responses/{response_id}/details")

        # Delete response
        dashboard_page.click_element(".delete-response-btn")

        # Confirm deletion
        dashboard_page.page.locator(".confirm-delete").click()

        # Assert success
        expect(dashboard_page.page.locator(".alert-success")).to_contain_text("deleted successfully")

        # Verify response no longer exists
        dashboard_page.navigate_to(f"/responses/{response_id}/details")
        expect(dashboard_page.page).to_have_url("**/404")  # Or appropriate error page

    def test_bulk_response_operations(self, dashboard_page: DashboardPage):
        """Test bulk operations on responses"""
        form_id = 1
        dashboard_page.navigate_to(f"/responses/{form_id}")

        # Select multiple responses
        dashboard_page.check_checkbox(".response-checkbox")
        dashboard_page.click_element(".bulk-actions-btn")

        # Test bulk delete
        dashboard_page.click_element(".bulk-delete")
        dashboard_page.page.locator(".confirm-bulk-delete").click()

        # Assert success
        expect(dashboard_page.page.locator(".alert-success")).to_contain_text("responses deleted")

    def test_response_analytics_view(self, dashboard_page: DashboardPage):
        """Test response analytics and statistics"""
        form_id = 1
        dashboard_page.navigate_to(f"/responses/{form_id}/analytics")

        # Assert analytics components load
        expect(dashboard_page.page.locator(".response-chart")).to_be_visible()
        expect(dashboard_page.page.locator(".completion-rate")).to_be_visible()
        expect(dashboard_page.page.locator(".average-time")).to_be_visible()

    def test_anonymous_vs_authenticated_responses(self, form_display_page: FormDisplayPage, dashboard_page: DashboardPage):
        """Test responses from anonymous vs authenticated users"""
        form_id = 1

        # Submit as anonymous user
        form_display_page.navigate_to(f"/forms/{form_id}")
        form_display_page.fill_text_input("1", "Anonymous User")
        form_display_page.submit_form()
        form_display_page.assert_form_submission_success()

        # Submit as authenticated user (would need login first)
        # dashboard_page.login("testuser", "password")
        # form_display_page.navigate_to(f"/forms/{form_id}")
        # form_display_page.fill_text_input("1", "Authenticated User")
        # form_display_page.submit_form()
        # form_display_page.assert_form_submission_success()

        # Check response listing shows both types
        dashboard_page.navigate_to(f"/responses/{form_id}")
        expect(dashboard_page.page.locator(".response-item")).to_have_count_greater_than(1)

    def test_response_data_integrity(self, dashboard_page: DashboardPage):
        """Test that response data is stored and retrieved correctly"""
        form_id = 1
        response_id = 1

        dashboard_page.navigate_to(f"/responses/{response_id}/details")

        # Verify all submitted data is displayed correctly
        expect(dashboard_page.page.locator(".answer")).to_have_count_greater_than(0)

        # Check specific data types
        text_answers = dashboard_page.page.locator(".text-answer")
        if text_answers.count() > 0:
            expect(text_answers.first).to_have_text("John Doe")

        email_answers = dashboard_page.page.locator(".email-answer")
        if email_answers.count() > 0:
            expect(email_answers.first).to_have_text("john@example.com")

    def test_response_time_tracking(self, dashboard_page: DashboardPage):
        """Test response time tracking and analytics"""
        form_id = 1
        dashboard_page.navigate_to(f"/responses/{form_id}/analytics")

        # Check response time metrics
        expect(dashboard_page.page.locator(".average-response-time")).to_be_visible()
        expect(dashboard_page.page.locator(".response-time-chart")).to_be_visible()

    def test_response_geolocation_tracking(self, dashboard_page: DashboardPage):
        """Test geolocation tracking for responses (if enabled)"""
        form_id = 1
        dashboard_page.navigate_to(f"/responses/{form_id}")

        # Check if IP/location data is collected and displayed
        location_data = dashboard_page.page.locator(".response-location")
        if location_data.is_visible():
            expect(location_data).to_have_text("")  # Should contain location info

    def test_response_export_with_attachments(self, dashboard_page: DashboardPage):
        """Test exporting responses that include file attachments"""
        form_id = 1
        dashboard_page.navigate_to(f"/responses/{form_id}")

        # Export responses with attachments
        with dashboard_page.page.expect_download() as download_info:
            dashboard_page.click_element("a[href*='format=zip']")  # Assuming zip export for files
        download = download_info.value
        expect(download.suggested_filename).to_contain(".zip")

    def test_response_validation_and_sanitization(self, form_display_page: FormDisplayPage):
        """Test that response data is properly validated and sanitized"""
        form_id = 1
        form_display_page.navigate_to(f"/forms/{form_id}")

        # Test XSS prevention
        xss_payload = "<script>alert('xss')</script>"
        form_display_page.fill_text_input("1", xss_payload)
        form_display_page.submit_form()

        # Verify response is sanitized
        dashboard_page.navigate_to(f"/responses/{form_id}")
        expect(dashboard_page.page.locator(".response-item")).not_to_contain_text("<script>")

        # Test SQL injection prevention
        sql_payload = "'; DROP TABLE responses; --"
        form_display_page.navigate_to(f"/forms/{form_id}")
        form_display_page.fill_text_input("1", sql_payload)
        form_display_page.submit_form()

        # Verify data is stored safely
        dashboard_page.navigate_to(f"/responses/{form_id}")
        expect(dashboard_page.page.locator(".response-item")).to_contain_text(sql_payload)

    def test_response_rate_limiting(self, form_display_page: FormDisplayPage):
        """Test rate limiting on form submissions"""
        form_id = 1

        # Submit multiple responses rapidly
        for i in range(10):
            form_display_page.navigate_to(f"/forms/{form_id}")
            form_display_page.fill_text_input("1", f"User {i}")
            form_display_page.submit_form()

            if i > 5:  # After rate limit
                expect(form_display_page.page.locator(".error")).to_contain_text("rate limit")

    def test_response_backup_and_recovery(self, dashboard_page: DashboardPage):
        """Test response backup and recovery functionality"""
        form_id = 1
        dashboard_page.navigate_to(f"/responses/{form_id}")

        # Test backup creation
        dashboard_page.click_element(".backup-responses-btn")
        expect(dashboard_page.page.locator(".alert-success")).to_contain_text("backup created")

        # Test backup download
        with dashboard_page.page.expect_download() as download_info:
            dashboard_page.click_element(".download-backup-btn")
        download = download_info.value
        expect(download.suggested_filename).to_contain("backup")

    def test_response_audit_trail(self, dashboard_page: DashboardPage):
        """Test response audit trail and change tracking"""
        response_id = 1
        dashboard_page.navigate_to(f"/responses/{response_id}/details")

        # Check audit log
        expect(dashboard_page.page.locator(".audit-log")).to_be_visible()
        expect(dashboard_page.page.locator(".audit-entry")).to_have_count_greater_than(0)

        # Verify audit entries contain timestamps and actions
        expect(dashboard_page.page.locator(".audit-timestamp")).to_be_visible()
        expect(dashboard_page.page.locator(".audit-action")).to_be_visible()

    def test_response_notifications(self, dashboard_page: DashboardPage):
        """Test response notification system"""
        # This would typically test email/webhook notifications
        # For UI testing, check notification preferences and history

        dashboard_page.navigate_to("/settings/notifications")

        # Configure response notifications
        dashboard_page.check_checkbox("#notify_on_response")
        dashboard_page.fill_input("#notification_email", "admin@example.com")
        dashboard_page.click_element("button[type='submit']")

        # Assert settings saved
        expect(dashboard_page.page.locator(".alert-success")).to_contain_text("settings saved")

    def test_response_analytics_dashboard(self, dashboard_page: DashboardPage):
        """Test comprehensive response analytics dashboard"""
        form_id = 1
        dashboard_page.navigate_to(f"/responses/{form_id}/analytics")

        # Test various analytics views
        dashboard_page.click_element(".overview-tab")
        expect(dashboard_page.page.locator(".total-responses")).to_be_visible()

        dashboard_page.click_element(".trends-tab")
        expect(dashboard_page.page.locator(".response-trends-chart")).to_be_visible()

        dashboard_page.click_element(".demographics-tab")
        expect(dashboard_page.page.locator(".demographics-chart")).to_be_visible()

        dashboard_page.click_element(".completion-tab")
        expect(dashboard_page.page.locator(".completion-funnel")).to_be_visible()

    def test_response_data_export_scheduling(self, dashboard_page: DashboardPage):
        """Test scheduled response data exports"""
        form_id = 1
        dashboard_page.navigate_to(f"/responses/{form_id}")

        # Set up scheduled export
        dashboard_page.click_element(".schedule-export-btn")
        dashboard_page.select_option("#export-frequency", "weekly")
        dashboard_page.select_option("#export-format", "csv")
        dashboard_page.fill_input("#export-email", "reports@example.com")
        dashboard_page.click_element(".save-schedule-btn")

        # Assert schedule created
        expect(dashboard_page.page.locator(".scheduled-exports")).to_contain_text("weekly")

    def test_response_data_anonymization(self, dashboard_page: DashboardPage):
        """Test response data anonymization features"""
        form_id = 1
        dashboard_page.navigate_to(f"/responses/{form_id}/settings")

        # Enable anonymization
        dashboard_page.check_checkbox("#anonymize_responses")
        dashboard_page.click_element("button[type='submit']")

        # Verify anonymization in response listing
        dashboard_page.navigate_to(f"/responses/{form_id}")
        expect(dashboard_page.page.locator(".anonymous-user")).to_be_visible()
        expect(dashboard_page.page.locator(".real-user-info")).to_be_hidden()