from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from module import db, create_db, MistakesLetters, WritingInformation, User, Text
from werkzeug.security import check_password_hash, generate_password_hash
import uuid
import json

app = Flask(__name__)

# PostgreSQL-Datenbankverbindung
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:postgres@localhost/tenfingers'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'supersecretkey'  # Für die Sitzungen (Sessions)

# Initialisiere die Datenbank und verknüpfe sie mit der App
create_db(app)

# Route für die Startseite


@app.route('/')
def home():
    if 'user_id' in session:  # Prüfen, ob der Benutzer eingeloggt ist
        return redirect(url_for('index'))  # Weiterleitung zur Index-Seite
    else:
        return redirect(url_for('login'))  # Weiterleitung zur Login-Seite


@app.route('/index')
def index():
    if 'user_id' in session:
        # Benutzer ist eingeloggt, Index-Seite anzeigen
        return render_template('index.html')
    else:
        flash('Bitte loggen Sie sich ein, um fortzufahren.')
        return redirect(url_for('login'))


# Login Route
@app.route("/login", methods=["GET", "POST"])
def login():
    """Zeigt die Login-Seite an und verarbeitet Login-Daten"""
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        try:
            # Benutzer anhand der E-Mail-Adresse suchen
            user = User.query.filter_by(email=email).first()

            # Debug-Ausgabe
            print(f"Benutzer gefunden: {user}")

            # Überprüfe das Passwort mit dem Passwort-Hash
            if user and check_password_hash(user.password_hash, password):
                # Benutzer-Session speichern
                session['user_id'] = user.user_id
                print(f"User-ID {user.user_id} in der Session gespeichert")

                # Weiterleitung zur Index-Seite nach erfolgreichem Login
                return redirect(url_for("index"))
            else:
                flash("Ungültige E-Mail oder Passwort")
                print("Ungültige E-Mail oder Passwort")

        except Exception as e:
            db.session.rollback()
            print(f"Fehler beim Login: {e}")
            flash("Ein Fehler ist aufgetreten")
            return "Ein Fehler ist aufgetreten"

    # GET-Anfrage: Zeige die Login-Seite an
    return render_template("login.html")


@app.route("/logout")
def logout():
    """Logs the user out by clearing the session"""
    session.pop('user_id', None)  # Benutzer aus der Session entfernen
    return redirect(url_for("login"))  # Nach dem Logout zur Login-Seite umleiten


@app.route("/dashboard")
def dashboard():
    """User Dashboard - nur für eingeloggte Benutzer"""
    if 'user_id' not in session:
        # Wenn der Benutzer nicht eingeloggt ist, zur Login-Seite umleiten
        return redirect(url_for("login"))

    # Logik für das Dashboard
    return f"Willkommen, Benutzer {session['user_id']}!"


@app.before_request
def require_login():
    """Prüft, ob der Benutzer eingeloggt ist, bevor geschützte Seiten aufgerufen werden"""
    # Liste von Routen, die ohne Login erreichbar sein sollen
    allowed_routes = ['login', 'register']

    # Prüfe, ob der Benutzer eingeloggt ist
    if 'user_id' not in session:
        # Leite zur Login-Seite weiter, wenn der Benutzer nicht eingeloggt ist
        if request.endpoint not in allowed_routes:
            return redirect(url_for('login'))

    else:
        # Benutzer ist in der Session, überprüfe, ob er in der Datenbank existiert
        user = User.query.filter_by(user_id=session['user_id']).first()
        if not user:
            # Wenn der Benutzer nicht in der Datenbank ist, zur Login-Seite umleiten
            session.pop('user_id', None)  # Benutzer aus der Session entfernen
            return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        password = request.form['password']
        birthdate = request.form['birthdate']  # Geburtsdatum aus dem Formular

        # Überprüfe, ob die E-Mail bereits existiert
        if User.query.filter_by(email=email).first():
            flash('Diese E-Mail wird bereits verwendet.')
            return redirect(url_for('register'))

        # Benutzer erstellen
        new_user = User(
            user_id=str(uuid.uuid4()),  # Erstelle eine eindeutige Benutzer-ID
            username=username,
            first_name=first_name,
            last_name=last_name,
            email=email,
            password_hash=generate_password_hash(password),
            birthdate=birthdate,  # Geburtsdatum speichern
            role='user'  # Rolle standardmäßig auf 'user' setzen
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
    user_id = session.get('user_id')  # Benutzer-ID aus der Session holen

    if not user_id or not text_id:
        return jsonify({"error": "Benutzer nicht eingeloggt oder Text nicht gefunden"}), 403

    # Schreibinformation bei Start des Tippvorgangs erstellen
    writing_info = WritingInformation(
        wi_id=str(uuid.uuid4()),  # Eindeutige ID
        user_id=user_id,
        text_id=text_id,
        mistake_count=0,  # Fehler sind zu Beginn 0
        time_spent_in_s=None,  # Zeit wird am Ende berechnet
        cpm=None,  # CPM wird am Ende berechnet
        ended_at=None  # Endzeit wird später gesetzt
    )
    db.session.add(writing_info)
    db.session.commit()  # created_at wird durch den Commit automatisch gesetzt

    return jsonify({"status": "success", "wi_id": writing_info.wi_id})


@app.route('/log_typing_errors', methods=['POST'])
def log_typing_errors():
    data = request.get_json()
    letter_mistakes = data.get('letterMistakes', [])
    wi_id = data.get('wi_id')  # wi_id vom Frontend übergeben
    user_id = session.get('user_id')  # Benutzer-ID aus der Session holen
    mistakes_counter = data.get('mistakes_counter', 0)  # Fehlerzähler vom Frontend

    if not user_id or not wi_id:
        return jsonify({"error": "Benutzer nicht eingeloggt oder Schreibinformationen nicht gefunden"}), 403

    # Schreibinformation laden
    writing_info = WritingInformation.query.filter_by(wi_id=wi_id).first()

    if writing_info is None:
        return jsonify({"error": "Schreibinformation nicht gefunden"}), 404

    # Tippfehler (Buchstaben) sofort in mistakes_letters speichern
    for mistake in letter_mistakes:
        mistakes_counter += 1  # Fehlerzähler erhöhen
        new_mistake = MistakesLetters(
            mpl_id=str(uuid.uuid4()),  # Eindeutige ID für jeden Fehler
            user_id=user_id,  # Benutzer-ID speichern
            letter=mistake['incorrect_letter'],
            expected_letter=mistake.get('expected_letter'),  # Der erwartete Buchstabe
            mistake_count=1
        )
        db.session.add(new_mistake)  # Fehler sofort speichern

    db.session.commit()  # Commit für die Tippfehler (mistakes_letters)

    # Fehlerzähler in writing_information speichern
    writing_info.mistake_count = mistakes_counter

    # Schreibinformation sollte erst aktualisiert werden, nachdem der Test abgeschlossen ist
    if data.get('test_completed'):  # Test abgeschlossen
        # Ende der Tippübung (aktuelle Zeit als Endzeit)
        ended_at = db.func.now()
        writing_info.ended_at = ended_at

        # Berechne die Zeitdifferenz in Sekunden
        time_spent_in_s = db.session.query(
            db.func.extract('epoch', writing_info.ended_at - writing_info.created_at)
        ).scalar()

        time_spent_in_s = round(time_spent_in_s)  # Zeit auf die Sekunde runden
        writing_info.time_spent_in_s = time_spent_in_s

        # Textlänge abrufen
        text = Text.query.filter_by(text_id=writing_info.text_id).first()
        text_length = text.text_length

        # Berechne CPM (Characters per Minute)
        if time_spent_in_s > 0:  # Vermeide Division durch 0
            cpm = (text_length / time_spent_in_s) * 60
        else:
            cpm = 0

        writing_info.cpm = round(cpm)  # CPM runden und speichern

        # Berechne die Genauigkeit
        if text_length > 0:
            accuracy = 1 - (writing_info.mistake_count / text_length)
            writing_info.acc = round(accuracy, 4) * 100 # Genauigkeit runden und speichern
        else:
            writing_info.acc = 0  # Falls keine Textlänge vorhanden ist

        db.session.commit()  # Commit für die Aktualisierung

    # Aktualisieren der Buchstabenstatistik in der users-Tabelle
    user = User.query.filter_by(user_id=user_id).first()

    # Sicherstellen, dass letter_stats als Dictionary existiert
    if user.letter_stats is None:
        user.letter_stats = {}

    # Falls letter_stats bereits Daten enthält, sicherstellen, dass es als Dictionary geladen wird
    if isinstance(user.letter_stats, str):
        user.letter_stats = json.loads(user.letter_stats)

    # Aktualisieren der Buchstabenstatistik
    for mistake in letter_mistakes:
        expected_letter = mistake['expected_letter']  # Den erwarteten Buchstaben verwenden

        # Wenn der Buchstabe bereits existiert, erhöhen wir den Zähler
        if expected_letter in user.letter_stats:
            user.letter_stats[expected_letter] += 1  # Zähler für den erwarteten Buchstaben erhöhen
        else:
            user.letter_stats[expected_letter] = 1  # Neuer Buchstabe hinzufügen und Zähler auf 1 setzen

    # Nach der Aktualisierung das Dictionary wieder als JSONB speichern
    user.letter_stats = json.dumps(user.letter_stats)

    db.session.commit()  # Letzter Commit, um die letter_stats zu speichern

    # Rückgabe einer erfolgreichen Antwort, um den Fehler zu beheben
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
        db.create_all()  # Erstellt die Tabellen in der Datenbank, falls sie nicht existieren
        print("Tabellen wurden erfolgreich erstellt.")
    app.run(debug=True)
