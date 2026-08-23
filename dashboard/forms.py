from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User

class EmployeeRegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    email = forms.EmailField(required=True)
    designation = forms.CharField(max_length=100, required=True, label="Job Role")
    department = forms.CharField(max_length=100, required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('first_name', 'last_name', 'email')
