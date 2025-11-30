import stripe
from flask import request, jsonify, current_app, redirect, url_for
from app import db
from app.payments import bp
from app.models import Form, Response, Payment

@bp.route('/<int:form_id>/create-checkout-session', methods=['POST'])
def create_checkout_session(form_id):
    """Create a new Stripe checkout session."""
    form = Form.query.get_or_404(form_id)
    if not form.settings.get('payment_amount'):
        return jsonify({'error': 'Payment amount not set for this form'}), 400

    try:
        checkout_session = stripe.checkout.Session.create(
            line_items=[
                {
                    'price_data': {
                        'currency': form.settings.get('payment_currency', 'usd'),
                        'product_data': {
                            'name': form.title,
                        },
                        'unit_amount': form.settings.get('payment_amount'),
                    },
                    'quantity': 1,
                },
            ],
            mode='payment',
            success_url=url_for('payments.success', _external=True),
            cancel_url=url_for('payments.cancel', _external=True),
        )
    except Exception as e:
        return jsonify(error=str(e)), 403

    return jsonify({'id': checkout_session.id})

@bp.route('/success')
def success():
    """Handle successful payments."""
    return "Payment successful!"

@bp.route('/cancel')
def cancel():
    """Handle canceled payments."""
    return "Payment canceled."

@bp.route('/webhook', methods=['POST'])
def webhook():
    """Handle Stripe webhooks."""
    event = None
    payload = request.data
    sig_header = request.headers.get('stripe-signature')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, current_app.config['STRIPE_WEBHOOK_SECRET']
        )
    except ValueError as e:
        # Invalid payload
        return jsonify(error=str(e)), 400
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return jsonify(error=str(e)), 400

    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        # Fulfill the purchase...
        print('Payment was successful.')
    else:
        print('Unhandled event type {}'.format(event['type']))

    return jsonify(success=True)
