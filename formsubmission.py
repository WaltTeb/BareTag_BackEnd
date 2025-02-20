#Flask-WTF
#2. Creating Form


from flask_wtf import Form
from wtforms import StringField, PasswordField, IntegerField, TextAreaField, SubmitField
from wtforms.validators import ValidationError, DataRequired

class RegistrationForm(Form):
    name = StringField(label="Username", validators = [DataRequired()])
    passWord = PasswordField(label="Password", validators = [DataRequired()])
    phoneNumber = IntegerField(label="Enter mobile number", validators=[DataRequired()])
    email = TextAreaField(label="email")
    submit = SubmitField("Send")