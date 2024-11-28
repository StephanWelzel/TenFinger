from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from module import db, create_db, MistakesLetters, WritingInformation, User, Text
from werkzeug.security import check_password_hash, generate_password_hash
import uuid
import json

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:postgres@localhost/tenfingers'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'supersecretkey'  # Für die Sitzungen (Sessions)

# Initialize the database and connect it with the app
create_db(app)

# Route for the start page
@app.route('/')
def home():
    if 'user_id' in session:  # Check if user is logged in
        return redirect(url_for('index'))  # If yes, go to index.html
    else:
        return redirect(url_for('login'))  # If no, back to login.html


@app.route('/index')
def index():
    if 'user_id' in session:
        return render_template('index.html')
    else:
        flash('Bitte loggen Sie sich ein, um fortzufahren.')
        return redirect(url_for('login'))


# Login Route
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        try:
            # Searching user with the email
            user = User.query.filter_by(email=email).first()

            # Debug-print
            print(f"Benutzer gefunden: {user}")

            # Checking password with the password hash
            if user and check_password_hash(user.password_hash, password):
                # Safe user session
                session['user_id'] = user.user_id
                print(f"User-ID {user.user_id} in der Session gespeichert")

                # Go to index.html after successfully logged in
                return redirect(url_for("index"))
            else:
                flash("Ungültige E-Mail oder Passwort")
                print("Ungültige E-Mail oder Passwort")

        except Exception as e:
            db.session.rollback()
            print(f"Fehler beim Login: {e}")
            flash("Ein Fehler ist aufgetreten")
            return "Ein Fehler ist aufgetreten"

    return render_template("login.html")


@app.route("/logout")
def logout():
    """Logs the user out by clearing the session"""
    session.pop('user_id', None)        # Delete user session
    return redirect(url_for("login"))   # After logging out, going back to login.html


@app.route("/dashboard")
def dashboard():
    """User Dashboard - nur für eingeloggte Benutzer"""
    if 'user_id' not in session:
        # If user is not logged in, back to login.html
        return redirect(url_for("login"))

    # Logic for the dashboard
    return f"Willkommen, Benutzer {session['user_id']}!"


@app.before_request
def require_login():
    """Prüft, ob der Benutzer eingeloggt ist, bevor geschützte Seiten aufgerufen werden"""
    # List of routes, that can be accessed without logged in
    allowed_routes = ['login', 'register']

    # Check if user is logged in
    if 'user_id' not in session:
        if request.endpoint not in allowed_routes:
            return redirect(url_for('login'))

    else:
        # User has a session, check in database if user exists
        user = User.query.filter_by(user_id=session['user_id']).first()
        if not user:
            # If user isn't in the database, back to login.html
            session.pop('user_id', None)  # Delete user from session
            return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        password = request.form['password']
        birthdate = request.form['birthdate']

        # Check if email exists
        if User.query.filter_by(email=email).first():
            flash('Diese E-Mail wird bereits verwendet.')
            return redirect(url_for('register'))

        # Create user
        new_user = User(
            user_id=str(uuid.uuid4()),  # Create a unique user id
            username=username,
            first_name=first_name,
            last_name=last_name,
            email=email,
            password_hash=generate_password_hash(password),
            birthdate=birthdate,
            role='user'                 # Role will be set to user
        )
        db.session.add(new_user)
        db.session.commit()

        flash('Registrierung erfolgreich! Sie können sich jetzt einloggen.')
        return redirect(url_for('login'))

    return render_template("register.html")


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
    for mistake in letter_mistakes:
        mistakes_counter += 1                       # Error counter +1
        new_mistake = MistakesLetters(
            mpl_id=str(uuid.uuid4()),               # Unique ID for every mistake
            user_id=user_id,
            letter=mistake['incorrect_letter'],
            expected_letter=mistake.get('expected_letter'),
            mistake_count=1
        )
        db.session.add(new_mistake)  # Save mistake immediately

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

    # If letter_stats already contains data, ensure that it is loaded as a dictionary
    if isinstance(user.letter_stats, str):
        user.letter_stats = json.loads(user.letter_stats)

    # Updating the letter statistics
    for mistake in letter_mistakes:
        expected_letter = mistake['expected_letter']

        # If the letter already exists, we increment the counter
        if expected_letter in user.letter_stats:
            user.letter_stats[expected_letter] += 1
        else:
            user.letter_stats[expected_letter] = 1

    # After updating, save the dictionary as JSONB again
    user.letter_stats = json.dumps(user.letter_stats)

    db.session.commit()  # Last commit to save the letter_stats

    return jsonify({"status": "success"})


@app.route('/get_texts', methods=['GET'])
def get_texts():
    texts = Text.query.all()
    if texts:
        print(f"Texte gefunden: {texts}")
    else:
        print("Keine Texte gefunden.")
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
        print("Tabellen wurden erfolgreich erstellt.")
    app.run(debug=True)
