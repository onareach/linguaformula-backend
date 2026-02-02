# models.py

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Formula(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    formula_name = db.Column(db.String(100), nullable=False)
    latex = db.Column(db.Text, nullable=False)
    display_order = db.Column(db.Integer)
    formula_description = db.Column(db.Text)
    english_verbalization = db.Column(db.Text)

    def __repr__(self):
        return f"<Formula {self.formula_name}>"

class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    problem_text = db.Column(db.Text, nullable=False)
    subject_area = db.Column(db.String(50))  # e.g., 'physics', 'statistics'
    # Image support for screenshot uploads
    image_filename = db.Column(db.String(255))  # Store filename/path of uploaded image
    image_data = db.Column(db.LargeBinary)  # Store binary image data
    image_text = db.Column(db.Text)  # Store extracted text from image (OCR/AI parsing)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    def __repr__(self):
        return f"<Application {self.title}>"

# Association table for many-to-many relationship between Applications and Formulas
application_formula = db.Table('application_formula',
    db.Column('application_id', db.Integer, db.ForeignKey('application.id'), primary_key=True),
    db.Column('formula_id', db.Integer, db.ForeignKey('formula.id'), primary_key=True),
    db.Column('relevance_score', db.Float),  # Optional: AI-generated relevance score
    db.Column('created_at', db.DateTime, default=db.func.current_timestamp())
)

# Add relationship to Application model
Application.formulas = db.relationship('Formula', secondary=application_formula, 
                                     backref=db.backref('applications', lazy='dynamic'))
