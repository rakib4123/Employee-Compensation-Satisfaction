from django import forms

from ml.generate_dataset import EDUCATION_POINTS, JOB_ROLES, LANGUAGE_LEVELS

JOB_ROLE_CHOICES = [(role, role) for role, *_ in JOB_ROLES]
EDUCATION_CHOICES = [(level, level) for level in EDUCATION_POINTS]
LANGUAGE_CHOICES = [(level, level) for level in LANGUAGE_LEVELS]

INPUT_CLASS = (
    "w-full rounded-lg border border-slate-300 dark:border-slate-600 "
    "bg-transparent dark:bg-slate-900 px-3 py-2 text-sm focus:outline-none focus:ring-2 "
    "focus:ring-indigo-500"
)

SLIDER_FIELDS = {"skills_score"}
SLIDER_CLASS = "w-full accent-indigo-600 cursor-pointer"


def _slider_widget():
    return forms.NumberInput(attrs={"type": "range", "min": 0, "max": 10, "step": 1, "class": SLIDER_CLASS})


class PredictProfileForm(forms.Form):
    job_role = forms.ChoiceField(choices=JOB_ROLE_CHOICES)
    age = forms.IntegerField(min_value=18, max_value=70)
    experience_years = forms.IntegerField(min_value=0, max_value=40)
    education_level = forms.ChoiceField(choices=EDUCATION_CHOICES)
    publications_count = forms.IntegerField(min_value=0, max_value=20)
    projects_led_count = forms.IntegerField(min_value=0, max_value=20)
    trainings_count = forms.IntegerField(min_value=0, max_value=20, initial=2, label="Trainings completed")
    skills_score = forms.IntegerField(min_value=0, max_value=10, initial=5, widget=_slider_widget())
    # boss_assessment_score is deliberately absent. It is a flat 10 for every
    # real employee, so a what-if run at any other value would model a profile
    # that cannot appear in the roster and could not be compared against it.
    # compensation.data.predict_profile injects the constant.
    language_proficiency = forms.ChoiceField(choices=LANGUAGE_CHOICES)
    proposed_salary = forms.IntegerField(min_value=0, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name in SLIDER_FIELDS:
                field.widget.attrs["oninput"] = f"document.getElementById('id_{name}_display').textContent = this.value"
            else:
                field.widget.attrs["class"] = INPUT_CLASS
