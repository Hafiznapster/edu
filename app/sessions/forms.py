from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, TextAreaField, DateTimeField, IntegerField, SubmitField, RadioField
from wtforms.validators import DataRequired, Length, NumberRange, ValidationError
from datetime import datetime

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
    session_type = RadioField('Session Type',
        choices=[('individual', 'Individual Session'), ('group', 'Group Session')],
        validators=[DataRequired()],
        default='individual'
    )
    max_participants = IntegerField('Maximum Participants', validators=[
        NumberRange(min=2, max=10, message='Group sessions can have 2-10 participants')
    ])
    submit = SubmitField('Request Session')
    
    def validate_max_participants(self, field):
        if self.session_type.data == 'individual' and field.data != 2:
            field.data = 2  # Force 2 participants for individual sessions
        elif self.session_type.data == 'group' and field.data < 3:
            raise ValidationError('Group sessions must allow at least 3 participants')


    def validate_scheduled_time(self, field):
        if field.data < datetime.now():
            raise ValidationError('Scheduled time must be in the future')

class ReviewForm(FlaskForm):
    rating = RadioField('Rating', choices=[(str(i), str(i)) for i in range(1, 6)],
                       validators=[DataRequired()], coerce=int)
    comment = TextAreaField('Comment', validators=[
        DataRequired(),
        Length(min=10, max=500, message='Comment must be between 10 and 500 characters')
    ])
    submit = SubmitField('Submit Review')

class FileUploadForm(FlaskForm):
    title = StringField('Title', validators=[
        DataRequired(),
        Length(min=3, max=200, message='Title must be between 3 and 200 characters')
    ])
    description = TextAreaField('Description', validators=[
        Length(max=1000, message='Description must be less than 1000 characters')
    ])
    file = FileField('File', validators=[
        FileRequired(),
        FileAllowed(['pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'txt', 'zip', 'rar', 'jpg', 'jpeg', 'png', 'gif'],
                   'Only common document, image, and archive formats are allowed')
    ])
    submit = SubmitField('Upload File')

class EndSessionForm(FlaskForm):
    submit = SubmitField('End Session')