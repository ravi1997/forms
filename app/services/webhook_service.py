import requests
from flask import current_app, jsonify
from app.models import Webhook

class WebhookService:
    @staticmethod
    def trigger_webhooks(form_id, event, payload):
        """
        Triggers all webhooks for a given form and event.
        """
        webhooks = Webhook.query.filter_by(form_id=form_id).all()
        for webhook in webhooks:
            if event in webhook.events:
                try:
                    requests.post(webhook.url, json=payload, timeout=5)
                except requests.exceptions.RequestException as e:
                    current_app.logger.error(f"Failed to trigger webhook {webhook.id}: {e}")
