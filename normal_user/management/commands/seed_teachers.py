import random
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from faker import Faker

# Models Import
from teachers.models import Teacher  # TeacherProfile ka naam yahan 'Teacher' hai
from organizations.models import Organization

User = get_user_model()
fake = Faker('en_IN')

class Command(BaseCommand):
    help = 'Sabhi schools mein Teachers aur unki Profiles create karne ke liye'

    def add_arguments(self, parser):
        parser.add_argument('total', type=int, help='Total kitne teachers banane hain?')

    def handle(self, *args, **kwargs):
        total = kwargs['total']
        
        all_orgs = list(Organization.objects.all())
        if not all_orgs:
            self.stdout.write(self.style.ERROR("Bhai, pehle Organization bana le!"))
            return

        self.stdout.write(self.style.WARNING(f"Shuru: {total} Teachers + Profiles load ho rahe hain..."))

        for i in range(total):
            try:
                with transaction.atomic():
                    # --- 1. User Data ---
                    first_name = fake.first_name()
                    last_name = fake.last_name()
                    mobile = f"{random.randint(6, 9)}{random.randint(100000000, 999999999)}"
                    
                    # Username logic: first 3 letters + last 4 mobile + 4 alpha key
                    user_key = fake.bothify(text='??##').lower()
                    username = f"{first_name[:3].lower()}{mobile[-4:]}{user_key}"
                    
                    user = User.objects.create_user(
                        username=username,
                        email=f"{username}@teacher.com",
                        password="Password@123",
                        first_name=first_name,
                        last_name=last_name,
                        mobile=mobile,
                        role=User.Roles.TEACHER,
                        gender=random.choice(['M', 'F']),
                        dob=fake.date_of_birth(minimum_age=25, maximum_age=50)
                    )

                    # --- 2. Teacher Profile Data (The Missing Link) ---
                    selected_org = random.choice(all_orgs)
                    
                    Teacher.objects.create(
                        user=user,
                        organization=selected_org,
                        bio=fake.paragraph(nb_sentences=3),
                        qualifications=random.choice(["B.Ed, M.Sc Physics", "M.A English, PhD", "B.Tech CS, M.Tech"]),
                        experience_years=random.randint(2, 15),
                        subject_expertise={
                            "primary": random.choice(["Maths", "Science", "English", "CS"]),
                            "secondary": ["General Knowledge", "Ethics"],
                            "levels": ["9-10", "11-12"],
                            "boards": ["CBSE", "ICSE"]
                        },
                        languages_spoken=["English", "Hindi"],
                        is_verified=True,
                        is_active_teacher=True,
                        preferred_mode='hybrid'
                    )

                    self.stdout.write(self.style.SUCCESS(f"Success: {username} created and linked to {selected_org.name}"))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error at {i}: {str(e)}"))

        self.stdout.write(self.style.SUCCESS(f"\nKaam ho gaya! Ab API hit kar, data milega."))