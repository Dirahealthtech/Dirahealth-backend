from datetime import datetime, timedelta, timezone
from sqlalchemy import Column, DateTime, String

from ..core.config import Config
from ..db.base import Base


class BlacklistedToken(Base):
    """
    Represents a JWT token that has been blacklisted and is no longer valid for authentication.

    Attributes:
        jti (str): The unique identifier (JWT ID) for the token, used as the primary key.
        expires_at (datetime): The UTC datetime when the blacklisted token expires.
    Methods:
        expiry_time(): Class method that returns the expiry time for a blacklisted token,
            calculated as the current UTC time plus the configured expiry duration.
    """

    __tablename__ = 'blacklisted_tokens'

    jti = Column(String(255), primary_key=True, index=True)
    expires_at = Column(DateTime, nullable=False)


    @classmethod
    def expiry_time(cls):
        """
        Calculates the expiry time for a token based on the current UTC time and the configured expiry duration.

        Returns:
            datetime: The UTC datetime when the token will expire.
        """

        return datetime.now(timezone.utc) + timedelta(minutes=Config.JTI_EXPIRY)
