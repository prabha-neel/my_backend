from django.contrib import admin
from .models import Exam, ExamSubject

# 1. Subjects ko Exam ke andar hi dikhane ke liye Inline class
class ExamSubjectInline(admin.TabularInline):
    model = ExamSubject
    extra = 1  # Kam se kam 1 khali row dikhegi naya subject jodne ke liye
    fields = ['subject_name', 'date', 'start_time', 'end_time', 'room_no', 'max_marks']

# 2. Main Exam Admin setup
@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    # Admin list view mein kaun-kaun se columns dikhenge
    list_display = ('exam_title', 'target_standard', 'start_date', 'status', 'organization')
    
    # Side mein filters (Taaki class ya status wise search kar sako)
    list_filter = ('status', 'target_standard', 'organization')
    
    # Search bar (Title se search karne ke liye)
    search_fields = ('exam_title', 'target_standard__name')
    
    # Inlines ka magic: Exam ke andar hi Subjects dikhenge
    inlines = [ExamSubjectInline]

    # Hidden fields ko read-only bana dete hain taaki koi galti se change na kare
    readonly_fields = ('external_id', 'created_at', 'updated_at', 'created_by')