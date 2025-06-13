from fastapi_mail import MessageSchema, MessageType
from typing import List, Dict, Any, Optional
from ..mails.send_mail import mail


class EmailService:

    async def create_message(self, recipients: list[str], subject: str, template_body: dict):
        """
        Creates an email message schema with the specified recipients, subject, and template body.

        Args:
            recipients (list[str]): A list of recipient email addresses.
            subject (str): The subject line of the email.
            template_body (dict): A dictionary containing dynamic values for the email template.

        Returns:
            MessageSchema: An instance of MessageSchema configured with the provided subject, recipients, and template body.
        """

        return MessageSchema(
            subject=subject,
            recipients=recipients,
            template_body=template_body,
            subtype=MessageType.html,
        )

    async def send_template_email(
        self, 
        to_email: str, 
        subject: str, 
        template_name: str, 
        context: Dict[str, Any]
    ) -> bool:
        """
        Sends an email using a template with provided context.

        Args:
            to_email (str): Recipient email address
            subject (str): Email subject
            template_name (str): Name of the template file (e.g., "order-tracking-update.html")
            context (Dict[str, Any]): Context variables for the template

        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        try:
            # Create message schema
            message = MessageSchema(
                subject=subject,
                recipients=[to_email],
                template_body=context,
                subtype=MessageType.html,
            )
            
            # Send the email
            await mail.send_message(message, template_name=template_name)
            return True
            
        except Exception as e:
            # Log the error (consider adding proper logging)
            print(f"Failed to send email: {str(e)}")
            return False
            
    async def send_order_confirmation(
        self,
        to_email: str,
        order_data: Dict[str, Any]
    ) -> bool:
        """
        Sends an order confirmation email.

        Args:
            to_email (str): Recipient email address
            order_data (Dict[str, Any]): Order details for the template

        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        subject = f"Order Confirmation - #{order_data.get('order_number', '')}"
        return await self.send_template_email(
            to_email=to_email,
            subject=subject,
            template_name="order-confirmation.html",
            context=order_data
        )
        
    async def send_order_tracking_update(
        self,
        to_email: str,
        order_data: Dict[str, Any],
        tracking_data: Dict[str, Any]
    ) -> bool:
        """
        Sends an order tracking update email.

        Args:
            to_email (str): Recipient email address
            order_data (Dict[str, Any]): Order details for the template
            tracking_data (Dict[str, Any]): Tracking details for the template

        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        # Different subject lines based on status
        status = tracking_data.get('status', '').lower()
        order_number = order_data.get('order_number', '')
        
        if status == "shipped":
            subject = f"Your Order #{order_number} Has Shipped!"
        elif status == "delivered":
            subject = f"Your Order #{order_number} Has Been Delivered"
        elif status == "processing":
            subject = f"Your Order #{order_number} is Being Processed"
        else:
            subject = f"Order #{order_number} Status Update"
            
        # Combine data for template
        template_data = {
            "order": order_data,
            "tracking": tracking_data,
            "customer_name": order_data.get("customer_name", "Valued Customer"),
            "customer_email": to_email,
            "current_year": order_data.get("current_year", "2024"),
            "tracking_detail_url": f"{order_data.get('frontend_url', '')}/orders/{order_data.get('id', '')}/tracking",
        }
        
        return await self.send_template_email(
            to_email=to_email,
            subject=subject,
            template_name="order-tracking-update.html",
            context=template_data
        )
