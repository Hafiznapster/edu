from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, TextAreaField, IntegerField, BooleanField, SelectField, DateField, TimeField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, Optional
from datetime import datetime

class GroupSessionForm(FlaskForm):
    """Form for creating a group session"""
    title = StringField('Session Title', validators=[DataRequired(), Length(min=5, max=100)])
    description = TextAreaField('Description', validators=[DataRequired(), Length(min=10, max=2000)])
    max_participants = IntegerField('Maximum Participants', validators=[DataRequired(), NumberRange(min=2, max=50)])
    scheduled_date = DateField('Date', validators=[DataRequired()], format='%Y-%m-%d')
    scheduled_time = TimeField('Time', validators=[DataRequired()], format='%H:%M')
    duration = IntegerField('Duration (minutes)', validators=[DataRequired(), NumberRange(min=15, max=240)])
    tags = StringField('Tags (comma separated)', validators=[Optional(), Length(max=200)])
    is_recurring = BooleanField('Recurring Session')
    recurrence_pattern = SelectField('Recurrence Pattern',
                                    choices=[('', 'Select Pattern'), ('weekly', 'Weekly'), ('bi-weekly', 'Bi-Weekly'), ('monthly', 'Monthly')],
                                    validators=[Optional()])
    submit = SubmitField('Create Session')

class ResourceLibraryForm(FlaskForm):
    """Form for creating a resource library"""
    title = StringField('Library Title', validators=[DataRequired(), Length(min=3, max=100)])
    description = TextAreaField('Description', validators=[DataRequired(), Length(min=10, max=1000)])
    category = SelectField('Category',
                          choices=[('programming', 'Programming'), ('design', 'Design'), ('business', 'Business'),
                                  ('science', 'Science'), ('language', 'Language'), ('other', 'Other')],
                          validators=[DataRequired()])
    is_public = BooleanField('Public Library')
    tags = StringField('Tags (comma separated)', validators=[Optional(), Length(max=200)])
    submit = SubmitField('Create Library')

class ResourceForm(FlaskForm):
    """Form for creating a resource"""
    title = StringField('Resource Title', validators=[DataRequired(), Length(min=3, max=100)])
    description = TextAreaField('Description', validators=[DataRequired(), Length(min=10, max=1000)])
    resource_type = SelectField('Resource Type',
                               choices=[('document', 'Document'), ('video', 'Video Link'),
                                       ('link', 'Web Link'), ('code_snippet', 'Code Snippet')],
                               validators=[DataRequired()])
    content = TextAreaField('Content/Link', validators=[Optional(), Length(max=5000)])
    file = FileField('Upload File', validators=[Optional(), FileAllowed(['pdf', 'doc', 'docx', 'ppt', 'pptx', 'txt', 'zip'])])
    submit = SubmitField('Create Resource')

class SessionNoteForm(FlaskForm):
    """Form for adding session notes"""
    content = TextAreaField('Note Content', validators=[DataRequired(), Length(min=10, max=5000)])
    is_private = BooleanField('Private Note (only visible to you)')
    submit = SubmitField('Add Note')

class SessionRecordingForm(FlaskForm):
    """Form for adding session recordings"""
    title = StringField('Recording Title', validators=[DataRequired(), Length(min=3, max=100)])
    recording_file = FileField('Upload Recording',
                              validators=[FileRequired(),
                                         FileAllowed(['mp4', 'webm', 'mp3', 'wav', 'ogg'], 'Audio/Video files only')])
    is_public = BooleanField('Make Public to All Participants')
    submit = SubmitField('Upload Recording')

# Progress Tracking Forms Removed

class MentorshipAgreementForm(FlaskForm):
    """Form for creating mentorship agreements"""
    goals = TextAreaField('Goals', validators=[DataRequired(), Length(min=10, max=2000)])
    expectations = TextAreaField('Expectations', validators=[DataRequired(), Length(min=10, max=2000)])
    meeting_frequency = SelectField('Meeting Frequency',
                                   choices=[('weekly', 'Weekly'), ('bi-weekly', 'Bi-Weekly'),
                                           ('monthly', 'Monthly'), ('as_needed', 'As Needed')],
                                   validators=[DataRequired()])
    communication_preferences = TextAreaField('Communication Preferences', validators=[DataRequired(), Length(min=10, max=1000)])
    confidentiality_terms = TextAreaField('Confidentiality Terms', validators=[DataRequired(), Length(min=10, max=2000)])
    termination_terms = TextAreaField('Termination Terms', validators=[DataRequired(), Length(min=10, max=2000)])
    end_date = DateField('End Date (Optional)', validators=[Optional()], format='%Y-%m-%d')
    submit = SubmitField('Create Agreement')

class SessionFeedbackForm(FlaskForm):
    """Form for session feedback"""
    rating = SelectField('Overall Rating',
                        choices=[(1, '1 - Poor'), (2, '2 - Fair'), (3, '3 - Good'),
                                (4, '4 - Very Good'), (5, '5 - Excellent')],
                        coerce=int, validators=[DataRequired()])
    comments = TextAreaField('Comments', validators=[DataRequired(), Length(min=10, max=1000)])
    submit = SubmitField('Submit Feedback')
