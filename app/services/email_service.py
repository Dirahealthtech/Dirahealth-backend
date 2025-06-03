from fastapi_mail import MessageSchema, MessageType


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
