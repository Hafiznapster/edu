from flask import render_template, flash, redirect, url_for, request, current_app
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.urls import url_parse
from app import db
from app.auth import bp
from app.auth.forms import LoginForm, RegistrationForm, ProfileForm
from app.models import User
from werkzeug.utils import secure_filename
import os

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        # Check if input is an email or username
        if '@' in form.username.data:
            user = User.query.filter_by(email=form.username.data).first()
        else:
            user = User.query.filter_by(username=form.username.data).first()

        if user is None or not user.check_password(form.password.data):
            flash('Invalid username/email or password')
            return redirect(url_for('auth.login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('main.dashboard')
        return redirect(next_page)
    return render_template('auth/login.html', title='Sign In', form=form)

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        user.role = 'mentor' if form.is_mentor.data else 'mentee'

        # Handle profile picture upload
        if form.profile_pic.data:
            filename = secure_filename(form.profile_pic.data.filename)
            form.profile_pic.data.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            user.profile_pic = filename

        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', title='Register', form=form)

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm()
    if form.validate_on_submit():
        current_user.bio = form.bio.data
        current_user.skills = form.skills.data
        current_user.availability = form.availability.data
        if form.profile_pic.data:
            filename = secure_filename(form.profile_pic.data.filename)
            form.profile_pic.data.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            current_user.profile_pic = filename
        db.session.commit()
        flash('Your profile has been updated.')
        return redirect(url_for('auth.profile'))
    elif request.method == 'GET':
        form.bio.data = current_user.bio
        form.skills.data = current_user.skills
        form.availability.data = current_user.availability
    return render_template('auth/profile.html', title='Profile', form=form)