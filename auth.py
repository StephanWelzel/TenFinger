from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from werkzeug.security import check_password_hash, generate_password_hash
from module import db, User
import uuid

auth_bp = Blueprint('auth', __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        try:
            user = User.query.filter_by(email=email).first()
            if user and check_password_hash(user.password_hash, password):
                session['user_id'] = user.user_id
                return redirect(url_for("index"))
            else:
                flash("Ungültige E-Mail oder Passwort")
                current_app.logger.warning("Ungültige E-Mail oder Passwort")
        except Exception:
            db.session.rollback()
            current_app.logger.exception("Fehler beim Login")
            flash("Ein Fehler ist aufgetreten")
            return "Ein Fehler ist aufgetreten", 500
    return render_template("login.html")

@auth_bp.route("/logout")
def logout():
    session.pop('user_id', None)
    return redirect(url_for("auth.login"))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        password = request.form['password']
        birthdate = request.form['birthdate']
        if User.query.filter_by(email=email).first():
            flash('Diese E-Mail wird bereits verwendet.')
            return redirect(url_for('auth.register'))
        new_user = User(
            user_id=str(uuid.uuid4()),
            username=username,
            first_name=first_name,
            last_name=last_name,
            email=email,
            password_hash=generate_password_hash(password),
            birthdate=birthdate,
            role='user'
        )
        db.session.add(new_user)
        db.session.commit()
        flash('Registrierung erfolgreich! Sie können sich jetzt einloggen.')
        return redirect(url_for('auth.login'))
    return render_template("register.html")
