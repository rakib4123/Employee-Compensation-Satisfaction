import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "buscom.settings")
django.setup()

from dashboard.models import User

hr = User.objects.filter(username="hr_admin").first()
if hr:
    hr.set_password("buscom-hr-2026")
    hr.save()

emp = User.objects.filter(username="amara_okafor").first()
if emp:
    emp.set_password("buscom-emp-2026")
    emp.save()

print("Passwords reset to default.")
