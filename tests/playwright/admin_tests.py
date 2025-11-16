import pytest
from playwright.sync_api import Page, expect
from page_objects.dashboard_page import DashboardPage


@pytest.fixture
def dashboard_page(page: Page):
    return DashboardPage(page)


class TestAdminFeatures:
    """Test administrative features and user management"""

    def test_admin_dashboard_access(self, dashboard_page: DashboardPage):
        """Test admin dashboard access and permissions"""
        # Login as admin first (assuming admin user exists)
        dashboard_page.navigate_to("/auth/login")
        # dashboard_page.login("admin", "adminpassword")

        # Navigate to admin dashboard
        dashboard_page.navigate_to("/admin")

        # Assert admin dashboard loads
        expect(dashboard_page.page.locator("h1")).to_contain_text("Admin Dashboard")

        # Check admin stats are displayed
        expect(dashboard_page.page.locator(".total-users")).to_be_visible()
        expect(dashboard_page.page.locator(".total-forms")).to_be_visible()
        expect(dashboard_page.page.locator(".total-responses")).to_be_visible()

    def test_admin_access_control(self, dashboard_page: DashboardPage):
        """Test that non-admin users cannot access admin features"""
        # Login as regular user
        dashboard_page.navigate_to("/auth/login")
        # dashboard_page.login("regularuser", "password")

        # Try to access admin dashboard
        dashboard_page.navigate_to("/admin")

        # Assert access denied
        expect(dashboard_page.page.locator(".access-denied")).to_be_visible()
        expect(dashboard_page.page).to_have_url(re.compile(r"/auth/login|/403"))

    def test_user_management_listing(self, dashboard_page: DashboardPage):
        """Test user management interface"""
        dashboard_page.navigate_to("/admin/users")

        # Assert user list loads
        expect(dashboard_page.page.locator(".user-list")).to_be_visible()
        expect(dashboard_page.page.locator(".user-item")).to_have_count_greater_than(0)

        # Check user details are displayed
        expect(dashboard_page.page.locator(".user-email")).to_be_visible()
        expect(dashboard_page.page.locator(".user-role")).to_be_visible()
        expect(dashboard_page.page.locator(".user-status")).to_be_visible()

    def test_user_role_management(self, dashboard_page: DashboardPage):
        """Test changing user roles"""
        user_id = 1  # Assuming test user exists
        dashboard_page.navigate_to(f"/admin/users/{user_id}/edit")

        # Change user role
        dashboard_page.select_option("#role", "moderator")
        dashboard_page.click_element("button[type='submit']")

        # Assert role updated
        expect(dashboard_page.page.locator(".alert-success")).to_contain_text("updated successfully")

        # Verify role change
        dashboard_page.navigate_to("/admin/users")
        expect(dashboard_page.page.locator(f"[data-user-id='{user_id}'] .user-role")).to_contain_text("moderator")

    def test_user_activation_deactivation(self, dashboard_page: DashboardPage):
        """Test activating and deactivating user accounts"""
        user_id = 1
        dashboard_page.navigate_to(f"/admin/users/{user_id}/edit")

        # Deactivate user
        dashboard_page.uncheck_checkbox("#is_active")
        dashboard_page.click_element("button[type='submit']")

        # Assert deactivation success
        expect(dashboard_page.page.locator(".alert-success")).to_contain_text("updated successfully")

        # Verify user is inactive
        dashboard_page.navigate_to("/admin/users")
        expect(dashboard_page.page.locator(f"[data-user-id='{user_id}']")).to_have_class("inactive")

        # Reactivate user
        dashboard_page.navigate_to(f"/admin/users/{user_id}/edit")
        dashboard_page.check_checkbox("#is_active")
        dashboard_page.click_element("button[type='submit']")

        # Verify user is active
        dashboard_page.navigate_to("/admin/users")
        expect(dashboard_page.page.locator(f"[data-user-id='{user_id}']")).to_have_class("active")

    def test_user_deletion(self, dashboard_page: DashboardPage):
        """Test deleting user accounts"""
        user_id = 1
        dashboard_page.navigate_to(f"/admin/users/{user_id}/edit")

        # Delete user
        dashboard_page.click_element(".delete-user-btn")

        # Confirm deletion
        dashboard_page.page.locator(".confirm-delete").click()

        # Assert deletion success
        expect(dashboard_page.page.locator(".alert-success")).to_contain_text("deleted successfully")

        # Verify user no longer exists
        dashboard_page.navigate_to("/admin/users")
        expect(dashboard_page.page.locator(f"[data-user-id='{user_id}']")).to_be_hidden()

    def test_bulk_user_operations(self, dashboard_page: DashboardPage):
        """Test bulk operations on users"""
        dashboard_page.navigate_to("/admin/users")

        # Select multiple users
        dashboard_page.check_checkbox(".user-checkbox")
        dashboard_page.click_element(".bulk-actions-btn")

        # Test bulk role change
        dashboard_page.select_option(".bulk-role", "editor")
        dashboard_page.click_element(".apply-bulk-role")

        # Assert bulk operation success
        expect(dashboard_page.page.locator(".alert-success")).to_contain_text("users updated")

    def test_admin_system_statistics(self, dashboard_page: DashboardPage):
        """Test system-wide statistics in admin dashboard"""
        dashboard_page.navigate_to("/admin")

        # Check system metrics
        expect(dashboard_page.page.locator(".system-stats")).to_be_visible()
        expect(dashboard_page.page.locator(".database-size")).to_be_visible()
        expect(dashboard_page.page.locator(".active-sessions")).to_be_visible()
        expect(dashboard_page.page.locator(".server-load")).to_be_visible()

    def test_admin_audit_logs(self, dashboard_page: DashboardPage):
        """Test admin audit log viewing"""
        dashboard_page.navigate_to("/admin/audit-logs")

        # Assert audit logs load
        expect(dashboard_page.page.locator(".audit-log")).to_be_visible()
        expect(dashboard_page.page.locator(".audit-entry")).to_have_count_greater_than(0)

        # Check audit entry details
        expect(dashboard_page.page.locator(".audit-timestamp")).to_be_visible()
        expect(dashboard_page.page.locator(".audit-user")).to_be_visible()
        expect(dashboard_page.page.locator(".audit-action")).to_be_visible()

    def test_admin_backup_management(self, dashboard_page: DashboardPage):
        """Test database backup and restore functionality"""
        dashboard_page.navigate_to("/admin/backups")

        # Create backup
        dashboard_page.click_element(".create-backup-btn")
        expect(dashboard_page.page.locator(".alert-success")).to_contain_text("backup created")

        # Download backup
        with dashboard_page.page.expect_download() as download_info:
            dashboard_page.click_element(".download-backup-btn")
        download = download_info.value
        expect(download.suggested_filename).to_contain("backup")

    def test_admin_system_settings(self, dashboard_page: DashboardPage):
        """Test system-wide settings management"""
        dashboard_page.navigate_to("/admin/settings")

        # Update system settings
        dashboard_page.fill_input("#site-name", "Updated Site Name")
        dashboard_page.check_checkbox("#maintenance-mode")
        dashboard_page.fill_input("#max-file-size", "50")
        dashboard_page.click_element("button[type='submit']")

        # Assert settings updated
        expect(dashboard_page.page.locator(".alert-success")).to_contain_text("settings updated")

    def test_admin_email_configuration(self, dashboard_page: DashboardPage):
        """Test email configuration in admin panel"""
        dashboard_page.navigate_to("/admin/email-settings")

        # Update email settings
        dashboard_page.fill_input("#smtp-server", "smtp.example.com")
        dashboard_page.fill_input("#smtp-port", "587")
        dashboard_page.fill_input("#smtp-username", "noreply@example.com")
        dashboard_page.fill_input("#smtp-password", "password123")
        dashboard_page.click_element("button[type='submit']")

        # Assert settings saved
        expect(dashboard_page.page.locator(".alert-success")).to_contain_text("email settings updated")

        # Test email sending
        dashboard_page.click_element(".test-email-btn")
        expect(dashboard_page.page.locator(".alert-success")).to_contain_text("test email sent")

    def test_admin_security_settings(self, dashboard_page: DashboardPage):
        """Test security settings management"""
        dashboard_page.navigate_to("/admin/security")

        # Update security settings
        dashboard_page.fill_input("#session-timeout", "60")
        dashboard_page.check_checkbox("#force-https")
        dashboard_page.fill_input("#password-min-length", "12")
        dashboard_page.check_checkbox("#two-factor-required")
        dashboard_page.click_element("button[type='submit']")

        # Assert security settings updated
        expect(dashboard_page.page.locator(".alert-success")).to_contain_text("security settings updated")

    def test_admin_performance_monitoring(self, dashboard_page: DashboardPage):
        """Test performance monitoring and metrics"""
        dashboard_page.navigate_to("/admin/performance")

        # Check performance metrics
        expect(dashboard_page.page.locator(".response-times")).to_be_visible()
        expect(dashboard_page.page.locator(".throughput")).to_be_visible()
        expect(dashboard_page.page.locator(".error-rates")).to_be_visible()
        expect(dashboard_page.page.locator(".memory-usage")).to_be_visible()

    def test_admin_log_management(self, dashboard_page: DashboardPage):
        """Test log file management"""
        dashboard_page.navigate_to("/admin/logs")

        # Assert logs are displayed
        expect(dashboard_page.page.locator(".log-entries")).to_be_visible()

        # Test log filtering
        dashboard_page.select_option(".log-level", "ERROR")
        dashboard_page.click_element(".filter-logs-btn")
        expect(dashboard_page.page.locator(".log-entry:not(.error)")).to_be_hidden()

        # Test log export
        with dashboard_page.page.expect_download() as download_info:
            dashboard_page.click_element(".export-logs-btn")
        download = download_info.value
        expect(download.suggested_filename).to_contain("logs")

    def test_admin_database_management(self, dashboard_page: DashboardPage):
        """Test database management features"""
        dashboard_page.navigate_to("/admin/database")

        # Check database status
        expect(dashboard_page.page.locator(".db-status")).to_be_visible()
        expect(dashboard_page.page.locator(".table-count")).to_be_visible()
        expect(dashboard_page.page.locator(".db-size")).to_be_visible()

        # Test database optimization
        dashboard_page.click_element(".optimize-db-btn")
        expect(dashboard_page.page.locator(".alert-success")).to_contain_text("database optimized")

    def test_admin_user_activity_monitoring(self, dashboard_page: DashboardPage):
        """Test monitoring user activity"""
        dashboard_page.navigate_to("/admin/user-activity")

        # Check activity metrics
        expect(dashboard_page.page.locator(".active-users")).to_be_visible()
        expect(dashboard_page.page.locator(".login-attempts")).to_be_visible()
        expect(dashboard_page.page.locator(".failed-logins")).to_be_visible()

        # Check recent activity
        expect(dashboard_page.page.locator(".recent-activity")).to_have_count_greater_than(0)

    def test_admin_content_moderation(self, dashboard_page: DashboardPage):
        """Test content moderation features"""
        dashboard_page.navigate_to("/admin/moderation")

        # Check reported content
        expect(dashboard_page.page.locator(".reported-content")).to_be_visible()

        # Test content approval/rejection
        dashboard_page.click_element(".approve-content-btn")
        expect(dashboard_page.page.locator(".alert-success")).to_contain_text("content approved")

        dashboard_page.click_element(".reject-content-btn")
        dashboard_page.fill_input(".rejection-reason", "Inappropriate content")
        dashboard_page.click_element(".confirm-rejection")
        expect(dashboard_page.page.locator(".alert-success")).to_contain_text("content rejected")

    def test_admin_api_management(self, dashboard_page: DashboardPage):
        """Test API key and access management"""
        dashboard_page.navigate_to("/admin/api-keys")

        # Generate new API key
        dashboard_page.click_element(".generate-api-key-btn")
        dashboard_page.fill_input(".key-name", "Test API Key")
        dashboard_page.click_element(".create-key-btn")

        # Assert key created
        expect(dashboard_page.page.locator(".api-key-list")).to_contain_text("Test API Key")

        # Test key permissions
        dashboard_page.click_element(".edit-permissions-btn")
        dashboard_page.check_checkbox(".read-permission")
        dashboard_page.check_checkbox(".write-permission")
        dashboard_page.click_element(".save-permissions-btn")

        # Assert permissions updated
        expect(dashboard_page.page.locator(".alert-success")).to_contain_text("permissions updated")

    def test_admin_notification_management(self, dashboard_page: DashboardPage):
        """Test system notification management"""
        dashboard_page.navigate_to("/admin/notifications")

        # Create system notification
        dashboard_page.click_element(".create-notification-btn")
        dashboard_page.fill_input(".notification-title", "System Maintenance")
        dashboard_page.fill_input(".notification-message", "Scheduled maintenance tonight")
        dashboard_page.select_option(".notification-type", "warning")
        dashboard_page.click_element(".send-notification-btn")

        # Assert notification sent
        expect(dashboard_page.page.locator(".alert-success")).to_contain_text("notification sent")

    def test_admin_export_system_data(self, dashboard_page: DashboardPage):
        """Test exporting system data for compliance"""
        dashboard_page.navigate_to("/admin/export")

        # Export user data
        with dashboard_page.page.expect_download() as download_info:
            dashboard_page.click_element(".export-users-btn")
        download = download_info.value
        expect(download.suggested_filename).to_contain("users")

        # Export system logs
        with dashboard_page.page.expect_download() as download_info:
            dashboard_page.click_element(".export-logs-btn")
        download = download_info.value
        expect(download.suggested_filename).to_contain("logs")

    def test_admin_maintenance_mode(self, dashboard_page: DashboardPage):
        """Test maintenance mode functionality"""
        dashboard_page.navigate_to("/admin/maintenance")

        # Enable maintenance mode
        dashboard_page.check_checkbox("#maintenance-mode")
        dashboard_page.fill_input("#maintenance-message", "System is under maintenance")
        dashboard_page.click_element("button[type='submit']")

        # Assert maintenance mode enabled
        expect(dashboard_page.page.locator(".alert-success")).to_contain_text("maintenance mode enabled")

        # Test that regular users see maintenance page
        # This would require opening a new incognito window
        context = dashboard_page.page.context.browser.new_context()
        new_page = context.new_page()
        new_page.goto("http://localhost:5000")
        expect(new_page.locator(".maintenance-message")).to_be_visible()
        context.close()

        # Disable maintenance mode
        dashboard_page.uncheck_checkbox("#maintenance-mode")
        dashboard_page.click_element("button[type='submit']")
        expect(dashboard_page.page.locator(".alert-success")).to_contain_text("maintenance mode disabled")

    def test_admin_error_monitoring(self, dashboard_page: DashboardPage):
        """Test error monitoring and alerting"""
        dashboard_page.navigate_to("/admin/errors")

        # Check error statistics
        expect(dashboard_page.page.locator(".error-count")).to_be_visible()
        expect(dashboard_page.page.locator(".error-rate")).to_be_visible()

        # Check recent errors
        expect(dashboard_page.page.locator(".error-list")).to_be_visible()

        # Test error alerting configuration
        dashboard_page.fill_input("#error-threshold", "10")
        dashboard_page.fill_input("#alert-email", "admin@example.com")
        dashboard_page.click_element(".save-alert-settings-btn")
        expect(dashboard_page.page.locator(".alert-success")).to_contain_text("alert settings saved")

    def test_admin_cross_browser_admin_features(self, dashboard_page: DashboardPage):
        """Test admin features work across browsers"""
        dashboard_page.navigate_to("/admin")

        # Basic functionality test - should work in all browsers
        expect(dashboard_page.page.locator(".admin-nav")).to_be_visible()
        expect(dashboard_page.page.locator(".admin-stats")).to_be_visible()

        # Test interactive elements
        dashboard_page.click_element(".admin-menu-toggle")
        expect(dashboard_page.page.locator(".admin-submenu")).to_be_visible()