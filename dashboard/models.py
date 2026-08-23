from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        HR = "hr", "HR"
        EMPLOYEE = "employee", "Employee"

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.EMPLOYEE)
