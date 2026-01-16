from datetime import datetime
from . import db

class DataValidationLog(db.Model):
    __tablename__ = 'data_validation_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    data_source_id = db.Column(db.Integer, db.ForeignKey('data_sources.id'), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False)
    validated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    total_records = db.Column(db.Integer)
    validation_errors = db.Column(db.JSON)
    
    @classmethod
    def create_log(cls, data_source, status, errors=None):
        log = cls(
            data_source_id=data_source.id,
            status=status,
            validation_errors=errors
        )
        db.session.add(log)
        db.session.commit()
        return log