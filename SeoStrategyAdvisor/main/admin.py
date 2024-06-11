from django.contrib import admin
from .models import ContactFormSubmission, Suggestion,Analysis

# Register your models here.
admin.site.register(Analysis)
admin.site.register(Suggestion)
admin.site.register(ContactFormSubmission)