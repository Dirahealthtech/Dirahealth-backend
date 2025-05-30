import enum


class UserRole(str, enum.Enum):
    CUSTOMER = "customer"
    ADMIN = "admin"
    SERVICE_TECH = "service_tech"
    SUPPLIER = "supplier"


class CustomerType(str, enum.Enum):
    INDIVIDUAL = "individual"
    HOSPITAL = "hospital"
    HEALTHCARE_PROVIDER = "healthcare_provider"


class AddressType(str, enum.Enum):
    BILLING = "billing"
    SHIPPING = "shipping"
    BOTH = "both"
