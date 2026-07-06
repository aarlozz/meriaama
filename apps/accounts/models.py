from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Central user model. `role` drives permissions across the whole system:
    - mother: normal app user, owns a HealthProfile
    - doctor / nurse / data_entry: hospital-side staff, access hospital_portal
    - admin: full Django admin access (use is_staff/is_superuser as usual)
    """

    class Role(models.TextChoices):
        MOTHER = "mother", "Mother"
        DOCTOR = "doctor", "Doctor"
        NURSE = "nurse", "Nurse"
        DATA_ENTRY = "data_entry", "Data Entry Operator"
        ADMIN = "admin", "Admin"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MOTHER)
    phone_number = models.CharField(max_length=20, blank=True)
    preferred_language = models.CharField(
        max_length=10,
        choices=[("en", "English"), ("ne", "Nepali")],
        default="en",
    )

    def is_hospital_staff(self):
        return self.role in {self.Role.DOCTOR, self.Role.NURSE, self.Role.DATA_ENTRY}

    def __str__(self):
        return f"{self.username} ({self.role})"