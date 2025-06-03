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


class AppointmentStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    RESCHEDULED = "rescheduled"

class LocationType(str, enum.Enum):
    ON_SITE = "on_site"
    CUSTOMER_LOCATION = "customer_location"

class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    REFUNDED = "refunded"
    FAILED = "failed"

class ReminderMethod(str, enum.Enum):
    EMAIL = "email"
    SMS = "sms"


class TransactionType(str, enum.Enum):
    PURCHASE = "purchase"
    SALE = "sale"
    RETURN = "return"
    ADJUSTMENT = "adjustment"
    WRITE_OFF = "write_off"
    TRANSFER = "transfer"


class ReferenceModel(str, enum.Enum):
    ORDER = "Order"
    PURCHASE_ORDER = "PurchaseOrder"
    STOCK_ADJUSTMENT = "StockAdjustment"


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"

class PaymentMethod(str, enum.Enum):
    MPESA = "mpesa"
    CARD = "card"
    BANK_TRANSFER = "bank_transfer"
    CASH = "cash"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"

class ProductType(str, enum.Enum):
    HOSPITAL_EQUIPMENT = "hospital_equipment"
    UPPER_LIMB_DEVICE = "upper_limb_device"
    LOWER_LIMB_DEVICE = "lower_limb_device"
    ACCESSORY = "accessory"
    CONSUMABLE = "consumable"


class DimensionUnit(str, enum.Enum):
    CM = "cm"
    INCH = "inch"


class WarrantyUnit(str, enum.Enum):
    DAYS = "days"
    MONTHS = "months"
    YEARS = "years"


class SupplierStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
