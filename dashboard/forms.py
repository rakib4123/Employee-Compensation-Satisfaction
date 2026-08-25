from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import DEPARTMENT_CHOICES, User

class EmployeeRegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    email = forms.EmailField(required=True)

    designation = forms.ChoiceField(choices=User.DESIGNATION_CHOICES, required=True, label="Job title")
    job_role_other = forms.CharField(max_length=100, required=False, label="If you selected 'Other' for your job title, please specify your role below:")
    department = forms.ChoiceField(
        choices=[("", "Select department")] + DEPARTMENT_CHOICES,
        required=False,
        label="Department",
    )

    # ML Features mapped from survey
    age = forms.IntegerField(min_value=18, max_value=100, required=True, label="Age")
    language_proficiency = forms.ChoiceField(choices=User.LANGUAGE_CHOICES, required=True, label="Language proficiency (English / primary work language)")
    experience_years = forms.IntegerField(min_value=0, max_value=50, required=True, label="How many years of professional experience do you have?")
    education_level = forms.ChoiceField(choices=User.EDUCATION_CHOICES, required=True, label="What is your highest completed education level?")

    # max_value=20 matches compensation/forms.py's PredictProfileForm, which
    # bounds these same fields for the HR what-if tool. Registration should
    # not be a looser gate than the internal tool onto the same model.
    publications_count = forms.IntegerField(min_value=0, max_value=20, required=True, label="How many professional publications, papers, or articles have you authored?")
    projects_led_count = forms.IntegerField(min_value=0, max_value=20, required=True, label="How many projects have you led or managed?")

    trainings_count = forms.IntegerField(min_value=0, max_value=20, required=True, label="How many trainings or courses have you completed?")
    skills_score = forms.IntegerField(min_value=0, max_value=10, required=True, label="Rate your current skill level for your role")

    # Compensation and Satisfaction
    # 1,000,000 BDT/month: generous headroom above the highest market band
    # max (Project Manager, 200,000/month in ml/generate_dataset.py's
    # JOB_ROLES) while still bounding how far a self-registering employee
    # can skew the HR dashboard's total payroll or the regression model.
    actual_salary = forms.IntegerField(min_value=0, max_value=1000000, required=True, label="What is your current monthly salary (BDT)?")
    satisfaction_score = forms.IntegerField(min_value=1, max_value=5, required=True, label="How satisfied are you with your current compensation?")
    fairness_feedback = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False, label="Anything that would make your compensation feel more fair?")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + (
            'first_name', 'last_name', 'email', 'age', 'designation', 'job_role_other', 'department',
            'language_proficiency', 'experience_years', 'education_level',
            'publications_count', 'projects_led_count', 'trainings_count', 'skills_score',
            'actual_salary', 'satisfaction_score', 'fairness_feedback'
        )

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("designation") == "Other" and not cleaned_data.get("department"):
            self.add_error("department", "Select a department for your role.")
        return cleaned_data
