from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from module import db, create_db, MistakesLetters, WritingInformation, User, Text
import uuid
import logging
from config import Config
from auth import auth_bp

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
app.config.from_object(Config)
app.register_blueprint(auth_bp)

# Initialize the database and connect it with the app
create_db(app)

# Route for the start page
@app.route('/')
def home():
    if 'user_id' in session:  # Check if user is logged in
        return redirect(url_for('index'))  # If yes, go to index.html
    else:
        return redirect(url_for('auth.login'))  # If no, back to login.html


@app.route('/index')
def index():
    if 'user_id' in session:
        return render_template('index.html')
    else:
        flash('Bitte loggen Sie sich ein, um fortzufahren.')
        return redirect(url_for('auth.login'))


# Dashboard Route
@app.route("/dashboard")
def dashboard():
    """User Dashboard - nur für eingeloggte Benutzer"""
    if 'user_id' not in session:
        # If user is not logged in, back to login.html
        return redirect(url_for("auth.login"))

    # Logic for the dashboard
    return f"Willkommen, Benutzer {session['user_id']}!"


@app.before_request
def require_login():
    """Prüft, ob der Benutzer eingeloggt ist, bevor geschützte Seiten aufgerufen werden"""
    # List of routes, that can be accessed without logged in
    allowed_routes = ['auth.login', 'auth.register', 'static']

    # Check if user is logged in
    if 'user_id' not in session:
        if request.endpoint not in allowed_routes:
            return redirect(url_for('auth.login'))

    else:
        # User has a session, check in database if user exists
        user = User.query.filter_by(user_id=session['user_id']).first()
        if not user:
            # If user isn't in the database, back to login.html
            session.pop('user_id', None)  # Delete user from session
            return redirect(url_for('auth.login'))




@app.route('/add_sample_texts')
def add_sample_texts():
    text1 = Text(text_id='T0001', content='Hallo Welt, wie geht es dir?')
    text2 = Text(text_id='T0002', content='Dies ist ein weiterer Testtext.')
    db.session.add(text1)
    db.session.add(text2)
    db.session.commit()
    return "Beispieltexte hinzugefügt!"


@app.route('/start_typing_session', methods=['POST'])
def start_typing_session():
    data = request.get_json()
    text_id = data.get('text_id')
    user_id = session.get('user_id')

    if not user_id or not text_id:
        return jsonify({"error": "Benutzer nicht eingeloggt oder Text nicht gefunden"}), 403

    # Create write information at the start of the typing process
    writing_info = WritingInformation(
        wi_id=str(uuid.uuid4()),
        user_id=user_id,
        text_id=text_id,
        mistake_count=0,        # Errors start at 0
        time_spent_in_s=None,   # Time will be added at the end
        cpm=None,               # CPM will be calculated at the end
        ended_at=None           # Time will be added at the end
    )
    db.session.add(writing_info)
    db.session.commit()  # created_at is set automatically by the commit

    return jsonify({"status": "success", "wi_id": writing_info.wi_id})


@app.route('/log_typing_errors', methods=['POST'])
def log_typing_errors():
    data = request.get_json()
    letter_mistakes = data.get('letterMistakes', [])
    wi_id = data.get('wi_id')                           # wi_id transferred from the frontend
    user_id = session.get('user_id')                    # Get user ID from the session
    mistakes_counter = data.get('mistakes_counter', 0)  # Error counter from the frontend

    if not user_id or not wi_id:
        return jsonify({"error": "Benutzer nicht eingeloggt oder Schreibinformationen nicht gefunden"}), 403

    # Loading writing information
    writing_info = WritingInformation.query.filter_by(wi_id=wi_id).first()

    if writing_info is None:
        return jsonify({"error": "Schreibinformation nicht gefunden"}), 404

    # Save typing errors (letters) immediately in mistakes_letters
    new_mistakes = []
    for mistake in letter_mistakes:
        mistakes_counter += 1                       # Error counter +1
        new_mistakes.append(
            MistakesLetters(
                mpl_id=str(uuid.uuid4()),           # Unique ID for every mistake
                user_id=user_id,
                letter=mistake['incorrect_letter'],
                expected_letter=mistake.get('expected_letter'),
                mistake_count=1
            )
        )
    if new_mistakes:
        db.session.add_all(new_mistakes)
        db.session.commit()  # Commit for the typos (mistakes_letters)

    # Save error counter in writing_information
    writing_info.mistake_count = mistakes_counter

    # Write information should only be updated after the test has been completed
    if data.get('test_completed'):  # Test finished
        # End of the typing exercise (current time as end time)
        ended_at = db.func.now()
        writing_info.ended_at = ended_at

        # Calculate the time difference in seconds
        time_spent_in_s = db.session.query(
            db.func.extract('epoch', writing_info.ended_at - writing_info.created_at)
        ).scalar()

        time_spent_in_s = round(time_spent_in_s)  # Round time to the second
        writing_info.time_spent_in_s = time_spent_in_s

        # Retrieve text length
        text = Text.query.filter_by(text_id=writing_info.text_id).first()
        text_length = text.text_length

        # Calculate CPM (Characters per Minute)
        if time_spent_in_s > 0:  # Avoid division by 0
            cpm = (text_length / time_spent_in_s) * 60
        else:
            cpm = 0

        writing_info.cpm = round(cpm)  # Round and save CPM

        # Calculate accuracy
        if text_length > 0:
            accuracy = 1 - (writing_info.mistake_count / text_length)
            writing_info.acc = round(accuracy, 4) * 100     # Round and save accuracy
        else:
            writing_info.acc = 0                            # If no text length is available

        db.session.commit()  # Commit for the update

    # Updating the letter statistics in the users table
    user = User.query.filter_by(user_id=user_id).first()

    # Ensure that letter_stats exists as a dictionary
    if user.letter_stats is None:
        user.letter_stats = {}

    # Updating the letter statistics
    for mistake in letter_mistakes:
        expected_letter = mistake['expected_letter']

        # If the letter already exists, we increment the counter
        if expected_letter in user.letter_stats:
            user.letter_stats[expected_letter] += 1
        else:
            user.letter_stats[expected_letter] = 1

    db.session.commit()  # Last commit to save the letter_stats

    return jsonify({"status": "success"})


@app.route('/get_texts', methods=['GET'])
def get_texts():
    texts = Text.query.all()
    if texts:
        app.logger.info("Texte gefunden: %s", texts)
    else:
        app.logger.info("Keine Texte gefunden.")
    text_list = [{'text_id': text.text_id, 'content': text.content} for text in texts]
    return jsonify(text_list)


@app.route('/get_text/<text_id>', methods=['GET'])
def get_text(text_id):
    text = Text.query.filter_by(text_id=text_id).first()
    if text:
        return jsonify({'text_id': text.text_id, 'content': text.content})
    else:
        return jsonify({'error': 'Text nicht gefunden'}), 404


if __name__ == '__main__':
    with app.app_context():
        db.create_all()         # Creates the tables in the database if they do not exist
        app.logger.info("Tabellen wurden erfolgreich erstellt.")
    app.run(debug=app.config.get('DEBUG', False))
