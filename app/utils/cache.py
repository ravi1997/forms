"""
Cache management utilities for the form builder application.
Provides functions for caching and invalidating analytics data.
"""
from app import cache
import json
from datetime import datetime
from app.models import Form


def get_cache_key(resource_type, resource_id, user_id=None, suffix=""):
    """Generate a standardized cache key."""
    if user_id:
        return f"{resource_type}:{resource_id}:user:{user_id}{suffix}"
    return f"{resource_type}:{resource_id}{suffix}"


def cache_form_analytics(form_id, analytics_data, timeout=300):
    """Cache form analytics data."""
    cache_key = get_cache_key("form_analytics", form_id)
    cache.set(cache_key, json.dumps(analytics_data), timeout=timeout)


def get_cached_form_analytics(form_id):
    """Get cached form analytics data, if available."""
    cache_key = get_cache_key("form_analytics", form_id)
    cached_data = cache.get(cache_key)
    if cached_data:
        return json.loads(cached_data)
    return None


def invalidate_form_analytics(form_id):
    """Invalidate cached form analytics data."""
    cache_key = get_cache_key("form_analytics", form_id)
    cache.delete(cache_key)


def cache_dashboard_stats(user_id, stats_data, timeout=300):
    """Cache dashboard statistics for a user."""
    cache_key = get_cache_key("dashboard_stats", "all", user_id)
    cache.set(cache_key, json.dumps(stats_data), timeout=timeout)


def get_cached_dashboard_stats(user_id):
    """Get cached dashboard statistics for a user, if available."""
    cache_key = get_cache_key("dashboard_stats", "all", user_id)
    cached_data = cache.get(cache_key)
    if cached_data:
        return json.loads(cached_data)
    return None


def invalidate_user_dashboard_stats(user_id):
    """Invalidate cached dashboard statistics for a user."""
    cache_key = get_cache_key("dashboard_stats", "all", user_id)
    cache.delete(cache_key)


def cache_form_responses(form_id, responses_data, timeout=180):
    """Cache form responses data."""
    cache_key = get_cache_key("form_responses", form_id)
    cache.set(cache_key, json.dumps(responses_data), timeout=timeout)


def get_cached_form_responses(form_id):
    """Get cached form responses data, if available."""
    cache_key = get_cache_key("form_responses", form_id)
    cached_data = cache.get(cache_key)
    if cached_data:
        return json.loads(cached_data)
    return None


def invalidate_form_responses(form_id):
    """Invalidate cached form responses data."""
    cache_key = get_cache_key("form_responses", form_id)
    cache.delete(cache_key)


def invalidate_all_form_cache(form_id):
    """Invalidate all cached data related to a form."""
    # Invalidate form analytics
    invalidate_form_analytics(form_id)
    # Invalidate form responses
    invalidate_form_responses(form_id)
    
    # Find the form and get its creator to invalidate their dashboard stats
    form = Form.query.get(form_id)
    if form:
        invalidate_user_dashboard_stats(form.created_by)


def invalidate_user_cache(user_id):
    """Invalidate all cached data related to a user."""
    # Invalidate user dashboard stats
    invalidate_user_dashboard_stats(user_id)
    
    # Invalidate analytics for all forms owned by the user
    from app.models import Form
    forms = Form.query.filter_by(created_by=user_id).all()
    for form in forms:
        invalidate_form_analytics(form.id)
        invalidate_form_responses(form.id)


def cache_user_engagement(user_id, engagement_data, timeout=600):
    """Cache user engagement metrics."""
    cache_key = get_cache_key("user_engagement", "metrics", user_id)
    cache.set(cache_key, json.dumps(engagement_data), timeout=timeout)


def get_cached_user_engagement(user_id):
    """Get cached user engagement metrics, if available."""
    cache_key = get_cache_key("user_engagement", "metrics", user_id)
    cached_data = cache.get(cache_key)
    if cached_data:
        return json.loads(cached_data)
    return None


def invalidate_user_engagement(user_id):
    """Invalidate cached user engagement metrics."""
    cache_key = get_cache_key("user_engagement", "metrics", user_id)
    cache.delete(cache_key)