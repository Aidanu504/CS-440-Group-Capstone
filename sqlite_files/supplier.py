from . import db

class Supplier(db.Model):
    __tablename__ = 'suppliers'
    id   = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)