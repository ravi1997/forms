from flask import render_template, request, jsonify, flash, redirect, url_for
from app import db
from app.webhooks import bp
from app.models import Form, Webhook
from app.utils.decorators import login_required, form_owner_required
from app.utils.helpers import log_route

@bp.route('/<int:form_id>/webhooks', methods=['GET'])
@log_route
@login_required
@form_owner_required
def list_webhooks(form_id, current_user_id, form):
    """List all webhooks for a form."""
    webhooks = Webhook.query.filter_by(form_id=form_id).all()
    return render_template('webhooks/list.html', form=form, webhooks=webhooks)

@bp.route('/<int:form_id>/webhooks/create', methods=['GET', 'POST'])
@log_route
@login_required
@form_owner_required
def create_webhook(form_id, current_user_id, form):
    """Create a new webhook for a form."""
    if request.method == 'POST':
        url = request.form.get('url')
        events = request.form.getlist('events')

        if not url or not events:
            flash('URL and at least one event are required.', 'error')
            return redirect(url_for('webhooks.create_webhook', form_id=form_id))

        webhook = Webhook(
            form_id=form_id,
            url=url,
            events=events
        )
        db.session.add(webhook)
        db.session.commit()
        flash('Webhook created successfully.', 'success')
        return redirect(url_for('webhooks.list_webhooks', form_id=form_id))

    return render_template('webhooks/create.html', form=form)

@bp.route('/webhooks/<int:webhook_id>/delete', methods=['POST'])
@log_route
@login_required
def delete_webhook(webhook_id, current_user_id):
    """Delete a webhook."""
    webhook = Webhook.query.get_or_404(webhook_id)
    form = webhook.form
    if form.created_by != current_user_id:
        flash('You do not have permission to delete this webhook.', 'error')
        return redirect(url_for('main.dashboard'))

    db.session.delete(webhook)
    db.session.commit()
    flash('Webhook deleted successfully.', 'success')
    return redirect(url_for('webhooks.list_webhooks', form_id=form.id))
