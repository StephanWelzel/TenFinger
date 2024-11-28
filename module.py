from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSONB

# Initialize the database
db = SQLAlchemy()

# Define the database schema with classes
class User(db.Model):
    __tablename__ = 'users'
    user_id = db.Column(db.String, primary_key=True)
    username = db.Column(db.String, unique=True, nullable=False)
    email = db.Column(db.String, unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String)                     # User/Admin etc.
    first_name = db.Column(db.String)
    last_name = db.Column(db.String)
    birthdate = db.Column(db.Date)
    account_type = db.Column(db.String)
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.now())
    letter_stats = db.Column(JSONB, nullable=True)  # A dict with all the mistakes done for each letter
                                                    # There could be a dict added, that count every letter typed,
                                                    # to create a percentage analysis on errors overall

    # Relationships (did not test it in this form yet)
    writing_sessions = db.relationship('WritingInformation', back_populates='user')
    mistakes = db.relationship('MistakesLetters', back_populates='user')

    # Function for setting up the password
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    # Function to check the password
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Text(db.Model):
    __tablename__ = 'texts'
    text_id = db.Column(db.String, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String)
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.now())
    text_length = db.Column(db.Integer)

    # Relationships (did not test it in this form yet)
    writing_sessions = db.relationship('WritingInformation', back_populates='text')

    def __init__(self, text_id, content):
        self.text_id = text_id
        self.content = content
        self.text_length = len(content)  # Automatically set the length based on content


class WritingInformation(db.Model):
    __tablename__ = 'writing_information'
    wi_id = db.Column(db.String, primary_key=True)
    text_id = db.Column(db.String, db.ForeignKey('texts.text_id'))
    user_id = db.Column(db.String, db.ForeignKey('users.user_id'))
    mistake_count = db.Column(db.Integer)
    time_spent_in_s = db.Column(db.Float)
    cpm = db.Column(db.Float)       # Characters per minute
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.now())
    ended_at = db.Column(db.TIMESTAMP)
    acc = db.Column(db.Numeric)     # Accuracy

    # Relationships (did not test it in this form yet)
    user = db.relationship('User', back_populates='writing_sessions')
    text = db.relationship('Text', back_populates='writing_sessions')

class MistakesLetters(db.Model):
    __tablename__ = 'mistakes_letters'
    mpl_id = db.Column(db.String, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey('users.user_id'))
    letter = db.Column(db.String(10))           # The letter pressed when doing a mistake
    expected_letter = db.Column(db.String(10))  # The letter that should be pressed when doing a mistake
    mistake_count = db.Column(db.Integer)
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.now())

    # Relationships (did not test it in this form yet)
    user = db.relationship('User', back_populates='mistakes')


# Function to create the database
def create_db(app):
    db.init_app(app)  # Link the app with the SQLAlchemy instance
    with app.app_context():  # Creates the tables within the app context
        db.create_all()
