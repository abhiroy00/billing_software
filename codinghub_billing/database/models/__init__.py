"""Import every model so Base.metadata is fully populated for create_all()."""
from database.models.course import Course
from database.models.customer import Customer
from database.models.expense import Expense, ExpenseCategory
from database.models.invoice import Invoice, InvoiceItem
from database.models.payment import Payment
from database.models.settings import AppSetting, BusinessSetting, InvoiceSetting
from database.models.user import Permission, Role, User, role_permissions

__all__ = [
    "Course",
    "Customer",
    "Expense",
    "ExpenseCategory",
    "Invoice",
    "InvoiceItem",
    "Payment",
    "AppSetting",
    "BusinessSetting",
    "InvoiceSetting",
    "Permission",
    "Role",
    "User",
    "role_permissions",
]
