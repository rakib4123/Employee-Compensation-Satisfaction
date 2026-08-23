from django.db import migrations


def seed_demo_users(apps, schema_editor):
    User = apps.get_model("dashboard", "User")
    if not User.objects.filter(username="hr_admin").exists():
        User.objects.create_user(
            username="hr_admin",
            email="hr@buscom.test",
            password="buscom-hr-2026",
            role="hr",
            first_name="Priya",
            last_name="Sharma",
        )
    if not User.objects.filter(username="amara_okafor").exists():
        User.objects.create_user(
            username="amara_okafor",
            email="amara.okafor@buscom.test",
            password="buscom-emp-2026",
            role="employee",
            first_name="Amara",
            last_name="Okafor",
        )


def unseed_demo_users(apps, schema_editor):
    User = apps.get_model("dashboard", "User")
    User.objects.filter(username__in=["hr_admin", "amara_okafor"]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("dashboard", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_demo_users, unseed_demo_users),
    ]
