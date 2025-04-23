from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, DateTimeField, IntegerField, SubmitField, DateField, TimeField
from wtforms.validators import DataRequired, Length, NumberRange

class SessionBookingForm(FlaskForm):
    topic = StringField('Topic', validators=[
        DataRequired(),
        Length(min=3, max=140, message='Topic must be between 3 and 140 characters')
    ])
    description = TextAreaField('Description', validators=[
        DataRequired(),
        Length(min=10, max=1000, message='Description must be between 10 and 1000 characters')
    ])
    scheduled_time = DateTimeField('Scheduled Time', validators=[
        DataRequired()
    ], format='%Y-%m-%dT%H:%M')
    duration = IntegerField('Duration (minutes)', validators=[
        DataRequired(),
        NumberRange(min=15, max=180, message='Duration must be between 15 and 180 minutes')
    ])
    submit = SubmitField('Request Session')

class MentorSearchForm(FlaskForm):
    skills = StringField('Skills', validators=[Length(min=0, max=200)])
    submit = SubmitField('Search')