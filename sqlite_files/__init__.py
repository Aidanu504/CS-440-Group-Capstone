from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from .product  import Product
from .customer import Customer
from .supplier import Supplier

__all__ = ['db', 'Product', 'Customer', 'Supplier']