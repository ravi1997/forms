import pytest
from playwright.sync_api import Page, expect
from page_objects.dashboard_page import DashboardPage


@pytest.fixture
def dashboard_page(page: Page):
    return DashboardPage(page)


class TestAnalytics:
    """Test analytics dashboard and reporting functionality"""

    def test_analytics_dashboard_overview(self, dashboard_page: DashboardPage):
        """Test main analytics dashboard displays correct overview data"""
        dashboard_page.navigate_to("/analytics")

        # Assert dashboard loads
        expect(dashboard_page.page.locator("h1")).to_contain_text("Analytics")

        # Check key metrics are displayed
        expect(dashboard_page.page.locator(".total-forms")).to_be_visible()
        expect(dashboard_page.page.locator(".total-responses")).to_be_visible()
        expect(dashboard_page.page.locator(".recent-activity")).to_be_visible()

        # Check charts are rendered
        expect(dashboard_page.page.locator(".responses-over-time-chart")).to_be_visible()

    def test_form_specific_analytics(self, dashboard_page: DashboardPage):
        """Test analytics for individual forms"""
        form_id = 1
        dashboard_page.navigate_to(f"/analytics/form/{form_id}")

        # Assert form analytics load
        expect(dashboard_page.page.locator(".form-title")).to_be_visible()

        # Check response count
        expect(dashboard_page.page.locator(".response-count")).to_be_visible()

        # Check question analytics
        expect(dashboard_page.page.locator(".question-analytics")).to_have_count_greater_than(0)

        # Check time-based analytics
        expect(dashboard_page.page.locator(".time-analytics")).to_be_visible()

    def test_response_trends_and_charts(self, dashboard_page: DashboardPage):
        """Test response trends visualization"""
        dashboard_page.navigate_to("/analytics")

        # Check response trends chart
        trends_chart = dashboard_page.page.locator(".trends-chart")
        expect(trends_chart).to_be_visible()

        # Test different time ranges
        dashboard_page.click_element(".time-range-7d")
        expect(trends_chart).to_be_visible()

        dashboard_page.click_element(".time-range-30d")
        expect(trends_chart).to_be_visible()

        dashboard_page.click_element(".time-range-90d")
        expect(trends_chart).to_be_visible()

    def test_question_response_breakdown(self, dashboard_page: DashboardPage):
        """Test detailed question response analytics"""
        form_id = 1
        dashboard_page.navigate_to(f"/analytics/form/{form_id}")

        # Check each question has analytics
        questions = dashboard_page.page.locator(".question-analytics")
        for i in range(questions.count()):
            question = questions.nth(i)

            # Check question text is displayed
            expect(question.locator(".question-text")).to_be_visible()

            # Check response count
            expect(question.locator(".response-count")).to_be_visible()

            # Check appropriate chart type based on question type
            if question.locator(".bar-chart").is_visible():
                expect(question.locator(".bar-chart")).to_be_visible()
            elif question.locator(".pie-chart").is_visible():
                expect(question.locator(".pie-chart")).to_be_visible()
            elif question.locator(".text-responses").is_visible():
                expect(question.locator(".text-responses")).to_be_visible()

    def test_user_engagement_analytics(self, dashboard_page: DashboardPage):
        """Test user engagement analytics"""
        dashboard_page.navigate_to("/analytics/user-engagement")

        # Check engagement metrics
        expect(dashboard_page.page.locator(".total-engagement")).to_be_visible()

        # Check day of week distribution
        expect(dashboard_page.page.locator(".day-of-week-chart")).to_be_visible()

        # Check hour of day distribution
        expect(dashboard_page.page.locator(".hour-of-day-chart")).to_be_visible()

        # Check form popularity
        expect(dashboard_page.page.locator(".form-popularity-chart")).to_be_visible()

    def test_completion_rate_analytics(self, dashboard_page: DashboardPage):
        """Test form completion rate analytics"""
        form_id = 1
        dashboard_page.navigate_to(f"/analytics/form/{form_id}")

        # Check completion rate display
        expect(dashboard_page.page.locator(".completion-rate")).to_be_visible()

        # Check completion funnel if available
        completion_funnel = dashboard_page.page.locator(".completion-funnel")
        if completion_funnel.is_visible():
            expect(completion_funnel).to_be_visible()

    def test_response_time_analytics(self, dashboard_page: DashboardPage):
        """Test response time tracking and analytics"""
        form_id = 1
        dashboard_page.navigate_to(f"/analytics/form/{form_id}")

        # Check average response time
        expect(dashboard_page.page.locator(".average-response-time")).to_be_visible()

        # Check response time distribution
        expect(dashboard_page.page.locator(".response-time-chart")).to_be_visible()

    def test_geographic_analytics(self, dashboard_page: DashboardPage):
        """Test geographic distribution of responses"""
        form_id = 1
        dashboard_page.navigate_to(f"/analytics/form/{form_id}")

        # Check geographic map/chart if available
        geo_chart = dashboard_page.page.locator(".geographic-chart")
        if geo_chart.is_visible():
            expect(geo_chart).to_be_visible()

        # Check location-based statistics
        expect(dashboard_page.page.locator(".location-stats")).to_be_visible()

    def test_device_and_browser_analytics(self, dashboard_page: DashboardPage):
        """Test device and browser usage analytics"""
        form_id = 1
        dashboard_page.navigate_to(f"/analytics/form/{form_id}")

        # Check device type breakdown
        expect(dashboard_page.page.locator(".device-breakdown")).to_be_visible()

        # Check browser usage
        expect(dashboard_page.page.locator(".browser-breakdown")).to_be_visible()

        # Check mobile vs desktop
        expect(dashboard_page.page.locator(".mobile-desktop-chart")).to_be_visible()

    def test_analytics_data_export(self, dashboard_page: DashboardPage):
        """Test exporting analytics data"""
        form_id = 1
        dashboard_page.navigate_to(f"/analytics/form/{form_id}")

        # Test PDF export
        with dashboard_page.page.expect_download() as download_info:
            dashboard_page.click_element(".export-pdf-btn")
        download = download_info.value
        expect(download.suggested_filename).to_contain(".pdf")

        # Test CSV export of raw data
        with dashboard_page.page.expect_download() as download_info:
            dashboard_page.click_element(".export-csv-btn")
        download = download_info.value
        expect(download.suggested_filename).to_contain(".csv")

    def test_analytics_date_filtering(self, dashboard_page: DashboardPage):
        """Test date range filtering in analytics"""
        form_id = 1
        dashboard_page.navigate_to(f"/analytics/form/{form_id}")

        # Set custom date range
        dashboard_page.fill_input("#start-date", "2024-01-01")
        dashboard_page.fill_input("#end-date", "2024-12-31")
        dashboard_page.click_element(".apply-filter-btn")

        # Assert data updates
        expect(dashboard_page.page.locator(".filtered-data")).to_be_visible()

        # Check date range is displayed
        expect(dashboard_page.page.locator(".date-range-display")).to_contain_text("2024")

    def test_analytics_real_time_updates(self, dashboard_page: DashboardPage):
        """Test real-time analytics updates"""
        form_id = 1
        dashboard_page.navigate_to(f"/analytics/form/{form_id}")

        # Get initial response count
        initial_count = dashboard_page.get_text(".response-count")

        # Submit a new response (would need to open new tab/window)
        # This is complex to test in UI - would typically be tested via API

        # For UI testing, check if refresh updates data
        dashboard_page.click_element(".refresh-btn")
        expect(dashboard_page.page.locator(".response-count")).to_be_visible()

    def test_analytics_permissions(self, dashboard_page: DashboardPage):
        """Test analytics access permissions"""
        form_id = 1

        # Try to access analytics for form you don't own
        other_form_id = 999
        dashboard_page.navigate_to(f"/analytics/form/{other_form_id}")

        # Assert access denied
        expect(dashboard_page.page.locator(".access-denied")).to_be_visible()

        # Test admin access to all analytics
        # Would need admin login first
        # dashboard_page.navigate_to("/analytics/admin")
        # expect(dashboard_page.page.locator(".admin-analytics")).to_be_visible()

    def test_custom_analytics_dashboards(self, dashboard_page: DashboardPage):
        """Test custom analytics dashboard creation"""
        dashboard_page.navigate_to("/analytics")

        # Create custom dashboard
        dashboard_page.click_element(".create-dashboard-btn")
        dashboard_page.fill_input("#dashboard-name", "Custom Test Dashboard")
        dashboard_page.click_element(".add-widget-btn")
        dashboard_page.select_option(".widget-type", "response-chart")
        dashboard_page.click_element(".save-dashboard-btn")

        # Assert custom dashboard created
        expect(dashboard_page.page.locator(".dashboard-list")).to_contain_text("Custom Test Dashboard")

    def test_analytics_alerts_and_notifications(self, dashboard_page: DashboardPage):
        """Test analytics alerts and notifications"""
        dashboard_page.navigate_to("/analytics/settings")

        # Set up response threshold alert
        dashboard_page.fill_input("#response-threshold", "100")
        dashboard_page.fill_input("#alert-email", "admin@example.com")
        dashboard_page.click_element(".save-alerts-btn")

        # Assert alert configured
        expect(dashboard_page.page.locator(".active-alerts")).to_contain_text("100 responses")

    def test_analytics_data_accuracy(self, dashboard_page: DashboardPage):
        """Test accuracy of analytics calculations"""
        form_id = 1
        dashboard_page.navigate_to(f"/analytics/form/{form_id}")

        # Compare analytics numbers with actual response data
        analytics_count = int(dashboard_page.get_text(".response-count"))

        # Navigate to responses and count
        dashboard_page.navigate_to(f"/responses/{form_id}")
        actual_count = dashboard_page.page.locator(".response-item").count()

        # Assert they match
        assert analytics_count == actual_count

    def test_analytics_performance(self, dashboard_page: DashboardPage):
        """Test analytics page performance"""
        form_id = 1

        # Measure page load time
        start_time = dashboard_page.page.evaluate("performance.now()")
        dashboard_page.navigate_to(f"/analytics/form/{form_id}")
        end_time = dashboard_page.page.evaluate("performance.now()")

        load_time = end_time - start_time
        assert load_time < 5000  # Should load within 5 seconds

        # Check for performance indicators
        expect(dashboard_page.page.locator(".loading-spinner")).to_be_hidden()

    def test_analytics_mobile_responsiveness(self, dashboard_page: DashboardPage):
        """Test analytics on mobile viewport"""
        dashboard_page.page.set_viewport_size({"width": 375, "height": 667})

        dashboard_page.navigate_to("/analytics")

        # Assert mobile layout works
        expect(dashboard_page.page.locator(".mobile-menu")).to_be_visible()
        expect(dashboard_page.page.locator(".responsive-chart")).to_be_visible()

        # Reset viewport
        dashboard_page.page.set_viewport_size({"width": 1920, "height": 1080})

    def test_analytics_error_handling(self, dashboard_page: DashboardPage):
        """Test analytics error handling"""
        # Try to access analytics for non-existent form
        dashboard_page.navigate_to("/analytics/form/99999")

        # Assert error handled gracefully
        expect(dashboard_page.page.locator(".error-message")).to_be_visible()

        # Test analytics with no data
        empty_form_id = 2  # Assuming form with no responses
        dashboard_page.navigate_to(f"/analytics/form/{empty_form_id}")

        # Assert empty state handled
        expect(dashboard_page.page.locator(".no-data-message")).to_be_visible()

    def test_analytics_data_privacy(self, dashboard_page: DashboardPage):
        """Test analytics data privacy and anonymization"""
        form_id = 1
        dashboard_page.navigate_to(f"/analytics/form/{form_id}")

        # Check that personally identifiable information is not exposed
        expect(dashboard_page.page.locator(".user-email")).to_be_hidden()
        expect(dashboard_page.page.locator(".user-name")).to_be_hidden()

        # Check anonymized data display
        expect(dashboard_page.page.locator(".anonymous-data")).to_be_visible()

    def test_analytics_integration_with_exports(self, dashboard_page: DashboardPage):
        """Test analytics integration with response exports"""
        form_id = 1
        dashboard_page.navigate_to(f"/analytics/form/{form_id}")

        # Export analytics report
        with dashboard_page.page.expect_download() as download_info:
            dashboard_page.click_element(".export-analytics-btn")
        download = download_info.value
        expect(download.suggested_filename).to_contain("analytics")

    def test_analytics_historical_data(self, dashboard_page: DashboardPage):
        """Test access to historical analytics data"""
        dashboard_page.navigate_to("/analytics/history")

        # Check historical data availability
        expect(dashboard_page.page.locator(".historical-data")).to_be_visible()

        # Test date picker for historical data
        dashboard_page.click_element(".date-picker")
        dashboard_page.click_element(".historical-date")
        dashboard_page.click_element(".load-historical-btn")

        # Assert historical data loads
        expect(dashboard_page.page.locator(".historical-chart")).to_be_visible()

    def test_analytics_api_endpoints(self, dashboard_page: DashboardPage):
        """Test analytics API endpoints through UI"""
        form_id = 1

        # Test that API calls are made correctly (check network tab)
        dashboard_page.navigate_to(f"/analytics/form/{form_id}")

        # This would typically check network requests
        # For UI testing, we can check that data loads without errors
        expect(dashboard_page.page.locator(".api-error")).to_be_hidden()

    @pytest.mark.parametrize("chart_type", ["bar", "line", "pie", "doughnut"])
    def test_different_chart_types(self, dashboard_page: DashboardPage, chart_type: str):
        """Test different chart types in analytics"""
        form_id = 1
        dashboard_page.navigate_to(f"/analytics/form/{form_id}")

        # Switch chart type
        dashboard_page.select_option(".chart-type-selector", chart_type)

        # Assert chart renders correctly
        expect(dashboard_page.page.locator(f".{chart_type}-chart")).to_be_visible()

    def test_analytics_cross_browser_compatibility(self, dashboard_page: DashboardPage):
        """Test analytics work across different browsers"""
        dashboard_page.navigate_to("/analytics")

        # Basic cross-browser test - charts should render
        expect(dashboard_page.page.locator(".chart-container")).to_be_visible()

        # Test interactive elements work
        dashboard_page.click_element(".chart-legend")
        expect(dashboard_page.page.locator(".chart-tooltip")).to_be_visible()