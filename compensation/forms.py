from django import forms

from ml.generate_dataset import EDUCATION_POINTS, JOB_ROLES, LANGUAGE_LEVELS

JOB_ROLE_CHOICES = [(role, role) for role, *_ in JOB_ROLES]
EDUCATION_CHOICES = [(level, level) for level in EDUCATION_POINTS]
LANGUAGE_CHOICES = [(level, level) for level in LANGUAGE_LEVELS]

INPUT_CLASS = (
    "w-full rounded-lg border border-slate-300 dark:border-slate-600 "
    "bg-transparent px-3 py-2 text-sm focus:outline-none focus:ring-2 "
    "focus:ring-indigo-500"
)


class PredictProfileForm(forms.Form):
    job_role = forms.ChoiceField(choices=JOB_ROLE_CHOICES)
    age = forms.IntegerField(min_value=18, max_value=70)
    experience_years = forms.IntegerField(min_value=0, max_value=40)
    education_level = forms.ChoiceField(choices=EDUCATION_CHOICES)
    publications_count = forms.IntegerField(min_value=0, max_value=20)
    projects_led_count = forms.IntegerField(min_value=0, max_value=20)
    training_score = forms.IntegerField(min_value=0, max_value=10)
    skills_score = forms.IntegerField(min_value=0, max_value=10)
    boss_assessment_score = forms.IntegerField(min_value=0, max_value=10)
    language_proficiency = forms.ChoiceField(choices=LANGUAGE_CHOICES)
    proposed_salary = forms.IntegerField(min_value=0, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = INPUT_CLASS
