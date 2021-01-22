from wtforms import *
from flask_security.forms import ConfirmRegisterForm


class ExampleFormSayHi(Form):
    who = StringField("", [validators.required(), validators.length(max=10)])
    submit = SubmitField('Submit')


class SecurityRegisterForm(ConfirmRegisterForm):
    """Custom Register Form."""
    email = StringField("Email")
    submit = SubmitField("submit")
