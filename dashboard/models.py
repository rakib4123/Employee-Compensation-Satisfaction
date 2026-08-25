from django.contrib.auth.models import AbstractUser
from django.db import models

from ml.generate_dataset import JOB_ROLES

ROLE_DEPARTMENTS = {role: department for role, department, _min, _max in JOB_ROLES}
DEPARTMENT_CHOICES = [(name, name) for name in sorted(set(ROLE_DEPARTMENTS.values()))]


class User(AbstractUser):
    class Role(models.TextChoices):
        HR = "hr", "HR"
        EMPLOYEE = "employee", "Employee"

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.EMPLOYEE)

    # ML dataset categorical fields
    EDUCATION_CHOICES = [
        ('PhD', 'PhD'),
        ('MSc', 'MSc'),
        ('BSc', 'BSc'),
        ('Diploma', 'Diploma'),
        ('High School', 'High School'),
    ]
    LANGUAGE_CHOICES = [
        ('Basic', 'Basic'),
        ('Intermediate', 'Intermediate'),
        ('Advanced', 'Advanced'),
        ('Fluent', 'Fluent'),
    ]

    DESIGNATION_CHOICES = [
        ('Software Engineer', 'Software Engineer'),
        ('Senior Software Engineer', 'Senior Software Engineer'),
        ('Data Analyst', 'Data Analyst'),
        ('QA Engineer', 'QA Engineer'),
        ('HR Executive', 'HR Executive'),
        ('HR Manager', 'HR Manager'),
        ('Accountant', 'Accountant'),
        ('Finance Manager', 'Finance Manager'),
        ('Sales Executive', 'Sales Executive'),
        ('Marketing Executive', 'Marketing Executive'),
        ('Project Manager', 'Project Manager'),
        ('Customer Support Executive', 'Customer Support Executive'),
        ('Graphic Designer', 'Graphic Designer'),
        ('Business Analyst', 'Business Analyst'),
        ('Operations Manager', 'Operations Manager'),
        ('Other', 'Other'),
    ]

    designation = models.CharField(max_length=100, choices=DESIGNATION_CHOICES, blank=True, null=True, verbose_name="Job Role")
    job_role_other = models.CharField(max_length=100, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True)
    education_level = models.CharField(max_length=50, choices=EDUCATION_CHOICES, blank=True, null=True)
    language_proficiency = models.CharField(max_length=50, choices=LANGUAGE_CHOICES, blank=True, null=True)

    # ML dataset numeric fields
    age = models.IntegerField(blank=True, null=True)
    experience_years = models.IntegerField(blank=True, null=True)
    publications_count = models.IntegerField(default=0, blank=True, null=True)
    projects_led_count = models.IntegerField(default=0, blank=True, null=True)
    
    # Performance metrics (out of 10)
    trainings_count = models.IntegerField(default=0, blank=True, null=True)
    skills_score = models.IntegerField(default=0, blank=True, null=True)
    boss_assessment_score = models.IntegerField(default=10, blank=True, null=True) # Hardcoded to 10 for now
    
    # Compensation & Satisfaction
    actual_salary = models.IntegerField(blank=True, null=True)
    satisfaction_score = models.IntegerField(blank=True, null=True)
    fairness_feedback = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.designation and self.designation != "Other":
            self.department = ROLE_DEPARTMENTS.get(self.designation, self.department)
        super().save(*args, **kwargs)
