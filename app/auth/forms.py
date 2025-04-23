from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, TextAreaField, FileField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
from app.models import User

class LoginForm(FlaskForm):
    username = StringField('Username or Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8, message='Password must be at least 8 characters long')])
    password2 = PasswordField('Repeat Password', validators=[DataRequired(), EqualTo('password')])
    is_mentor = BooleanField('Register as Mentor')
    profile_pic = FileField('Profile Picture')
    submit = SubmitField('Register')

    def validate_password(self, password):
        # Check if password contains @ symbol
        if '@' not in password.data:
            raise ValidationError('Password must contain @ symbol')

        # Check if password contains at least one number
        if not any(char.isdigit() for char in password.data):
            raise ValidationError('Password must contain at least one number')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')

class ProfileForm(FlaskForm):
    bio = TextAreaField('About me', validators=[Length(min=0, max=500)])
    skills = StringField('Skills (comma separated)', validators=[Length(min=0, max=200)])
    availability = TextAreaField('Availability', validators=[Length(min=0, max=500)])
    profile_pic = FileField('Profile Picture')
    submit = SubmitField('Update Profile')