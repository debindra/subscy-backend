import aiosmtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Optional
from jinja2 import Template


class EmailService:
    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_password = os.getenv("SMTP_PASS")
        self.email_from = os.getenv("EMAIL_FROM", self.smtp_user)
        self.smtp_secure = os.getenv("SMTP_SECURE", "false").lower() == "true"
        
    @staticmethod
    def _get_reminder_template() -> str:
        """Returns HTML email template for subscription reminders"""
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Subscription Renewal Reminder</title>
</head>
<body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #f4f4f4;">
    <table role="presentation" style="width: 100%; border-collapse: collapse;">
        <tr>
            <td style="padding: 20px 0; text-align: center; background-color: #6366f1;">
                <h1 style="margin: 0; color: #ffffff; font-size: 24px;">Subscription Tracker</h1>
            </td>
        </tr>
        <tr>
            <td style="padding: 40px 20px;">
                <table role="presentation" style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <tr>
                        <td style="padding: 40px 30px;">
                            <h2 style="margin: 0 0 20px 0; color: #333333; font-size: 24px;">
                                🔔 Upcoming Subscription Renewal
                            </h2>
                            <p style="margin: 0 0 20px 0; color: #666666; font-size: 16px; line-height: 1.6;">
                                Hello {{ user_name }},
                            </p>
                            <p style="margin: 0 0 30px 0; color: #666666; font-size: 16px; line-height: 1.6;">
                                This is a reminder that your subscription <strong>{{ subscription_name }}</strong> will renew soon.
                            </p>
                            
                            <table role="presentation" style="width: 100%; margin: 30px 0; border-collapse: collapse; background-color: #f9fafb; border-radius: 6px;">
                                <tr>
                                    <td style="padding: 20px;">
                                        <table role="presentation" style="width: 100%; border-collapse: collapse;">
                                            <tr>
                                                <td style="padding: 8px 0; color: #666666; font-size: 14px; width: 40%;">Subscription:</td>
                                                <td style="padding: 8px 0; color: #333333; font-size: 14px; font-weight: bold;">{{ subscription_name }}</td>
                                            </tr>
                                            <tr>
                                                <td style="padding: 8px 0; color: #666666; font-size: 14px;">Renewal Date:</td>
                                                <td style="padding: 8px 0; color: #333333; font-size: 14px; font-weight: bold;">{{ renewal_date }}</td>
                                            </tr>
                                            <tr>
                                                <td style="padding: 8px 0; color: #666666; font-size: 14px;">Amount:</td>
                                                <td style="padding: 8px 0; color: #333333; font-size: 14px; font-weight: bold;">{{ currency }} {{ amount }}</td>
                                            </tr>
                                            <tr>
                                                <td style="padding: 8px 0; color: #666666; font-size: 14px;">Billing Cycle:</td>
                                                <td style="padding: 8px 0; color: #333333; font-size: 14px; font-weight: bold;">{{ billing_cycle }}</td>
                                            </tr>
                                            {% if category %}
                                            <tr>
                                                <td style="padding: 8px 0; color: #666666; font-size: 14px;">Category:</td>
                                                <td style="padding: 8px 0; color: #333333; font-size: 14px; font-weight: bold;">{{ category }}</td>
                                            </tr>
                                            {% endif %}
                                            {% if days_until > 0 %}
                                            <tr>
                                                <td style="padding: 8px 0; color: #666666; font-size: 14px;">Days Until Renewal:</td>
                                                <td style="padding: 8px 0; color: #e67e22; font-size: 14px; font-weight: bold;">{{ days_until }} days</td>
                                            </tr>
                                            {% else %}
                                            <tr>
                                                <td style="padding: 8px 0; color: #666666; font-size: 14px;">Status:</td>
                                                <td style="padding: 8px 0; color: #e74c3c; font-size: 14px; font-weight: bold;">Renews today!</td>
                                            </tr>
                                            {% endif %}
                                        </table>
                                    </td>
                                </tr>
                            </table>
                            
                            {% if website %}
                            <p style="margin: 20px 0; text-align: center;">
                                <a href="{{ website }}" style="display: inline-block; padding: 12px 30px; background-color: #6366f1; color: #ffffff; text-decoration: none; border-radius: 6px; font-weight: bold;">Manage Subscription</a>
                            </p>
                            {% endif %}
                            
                            <p style="margin: 30px 0 0 0; color: #999999; font-size: 12px; line-height: 1.6; text-align: center;">
                                This is an automated reminder from Subscription Tracker.<br>
                                You can manage your reminder preferences in your account settings.
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
        <tr>
            <td style="padding: 20px; text-align: center; color: #999999; font-size: 12px;">
                <p style="margin: 0;">© 2025 Subscription Tracker. All rights reserved.</p>
            </td>
        </tr>
    </table>
</body>
</html>
        """
    
    def _render_template(self, template_str: str, context: Dict) -> str:
        """Render Jinja2 template with context"""
        template = Template(template_str)
        return template.render(**context)
    
    async def send_reminder_email(
        self,
        to_email: str,
        user_name: str,
        subscription: Dict,
        days_until: int
    ) -> bool:
        """Send reminder email for upcoming subscription renewal"""
        if not self.smtp_user or not self.smtp_password:
            print("Warning: SMTP credentials not configured. Email reminders disabled.")
            return False
        
        try:
            # Format renewal date
            renewal_date = subscription.get("nextRenewalDate", "")
            if renewal_date:
                from datetime import datetime
                try:
                    if "T" in renewal_date:
                        dt = datetime.fromisoformat(renewal_date.replace("Z", "+00:00"))
                        renewal_date = dt.strftime("%B %d, %Y")
                    else:
                        dt = datetime.strptime(renewal_date, "%Y-%m-%d")
                        renewal_date = dt.strftime("%B %d, %Y")
                except:
                    pass
            
            # Format billing cycle
            billing_cycle = subscription.get("billingCycle", "monthly").capitalize()
            
            # Prepare email context
            context = {
                "user_name": user_name or "User",
                "subscription_name": subscription.get("name", "Subscription"),
                "renewal_date": renewal_date,
                "amount": f"{subscription.get('amount', 0):.2f}",
                "currency": subscription.get("currency", "USD"),
                "billing_cycle": billing_cycle,
                "category": subscription.get("category", ""),
                "website": subscription.get("website"),
                "days_until": days_until
            }
            
            # Create message
            message = MIMEMultipart("alternative")
            message["From"] = self.email_from
            message["To"] = to_email
            message["Subject"] = f"🔔 Reminder: {subscription.get('name', 'Subscription')} renews in {days_until} day{'s' if days_until != 1 else ''}"
            
            # Create HTML content
            html_content = self._render_template(EmailService._get_reminder_template(), context)
            
            # Create plain text version
            text_content = f"""
Subscription Renewal Reminder

Hello {context['user_name']},

This is a reminder that your subscription "{context['subscription_name']}" will renew soon.

Subscription: {context['subscription_name']}
Renewal Date: {context['renewal_date']}
Amount: {context['currency']} {context['amount']}
Billing Cycle: {context['billing_cycle']}
Days Until Renewal: {days_until} day{'s' if days_until != 1 else ''}

This is an automated reminder from Subscription Tracker.
            """
            
            # Attach both versions
            part1 = MIMEText(text_content, "plain")
            part2 = MIMEText(html_content, "html")
            message.attach(part1)
            message.attach(part2)
            
            # Send email
            try:
                if self.smtp_secure:
                    await aiosmtplib.send(
                        message,
                        hostname=self.smtp_host,
                        port=self.smtp_port,
                        use_tls=True,
                        username=self.smtp_user,
                        password=self.smtp_password,
                    )
                else:
                    await aiosmtplib.send(
                        message,
                        hostname=self.smtp_host,
                        port=self.smtp_port,
                        start_tls=True,
                        username=self.smtp_user,
                        password=self.smtp_password,
                    )
                
                print(f"Reminder email sent successfully to {to_email} for subscription: {subscription.get('name')}")
                return True
            except Exception as send_error:
                print(f"Error sending email to {to_email}: {str(send_error)}")
                return False
            
        except Exception as e:
            print(f"Error sending reminder email to {to_email}: {str(e)}")
            import traceback
            traceback.print_exc()
            return False


# Singleton instance  
email_service = EmailService()

