import random
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from faker import Faker

# Models Import
from students.models import StudentProfile
from organizations.models import Organization
from students_classroom.models import Standard 

User = get_user_model()
fake = Faker('en_IN')

class Command(BaseCommand):
    help = 'Sabhi schools aur sabhi classes mein students distribute karne ke liye'

    def add_arguments(self, parser):
        parser.add_argument('total', type=int, help='Total kitne students banane hain?')

    def handle(self, *args, **kwargs):
        total = kwargs['total']
        
        # 1. Saare Schools (Organizations) ki list nikal lo
        all_orgs = list(Organization.objects.all())
        if not all_orgs:
            self.stdout.write(self.style.ERROR("Bhai, kam se kam ek School toh bana le!"))
            return

        # 2. Saari Classes (Standards) ki list nikal lo
        all_standards = list(Standard.objects.all())
        if not all_standards:
            self.stdout.write(self.style.ERROR("Bhai, 'Standard' table khali hai!"))
            return

        self.stdout.write(self.style.WARNING(f"Shuru kar rahe hain: {total} students ko {len(all_orgs)} schools mein divide karenge..."))

        for i in range(total):
            try:
                with transaction.atomic():
                    # --- A. User Data Generation ---
                    first_name = fake.first_name()
                    last_name = fake.last_name()
                    mobile = f"{random.randint(6, 9)}{random.randint(100000000, 999999999)}"
                    
                    # Tera special username logic (instructions ke hisaab se)
                    user_key = fake.bothify(text='??##').lower()
                    username = f"{first_name[:3].lower()}{mobile[-4:]}{user_key}"
                    
                    email = f"{username}@school.com"

                    user = User.objects.create_user(
                        username=username,
                        email=email,
                        password="Password@123",
                        first_name=first_name,
                        last_name=last_name,
                        mobile=mobile,
                        role=User.Roles.STUDENT,
                        gender=random.choice(['M', 'F']),
                        dob=fake.date_of_birth(minimum_age=5, maximum_age=18)
                    )

                    # --- B. Smart Distribution ---
                    # Har loop mein naya random school aur random class pick hogi
                    selected_org = random.choice(all_orgs)
                    selected_class = random.choice(all_standards)

                    StudentProfile.objects.create(
                        user=user,
                        organization=selected_org,
                        student_unique_id=f"STU-{random.randint(10000, 99999)}",
                        current_standard=selected_class,
                        is_active=True,
                        bio=f"Student of {selected_class.name} at {selected_org.name}"
                    )

                    self.stdout.write(self.style.SUCCESS(f"Done: {username} -> {selected_org.name} ({selected_class})"))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Galti loop {i} mein: {str(e)}"))

        self.stdout.write(self.style.SUCCESS(f"\nMubarak ho! {total} students sabhi schools mein load ho gaye."))