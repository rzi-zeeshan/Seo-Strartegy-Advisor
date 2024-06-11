# models.py
from django.db import models
from django.contrib.auth.models import User

class Analysis(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    url = models.URLField()
    keywords = models.TextField()
    content = models.TextField()
    keyword_analysis = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Analysis by {self.user.username} - {self.url}"

class OptimizedFactor(models.Model):
    analysis = models.ForeignKey(Analysis, on_delete=models.CASCADE)
    factor = models.CharField(max_length=255)
    detail = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Optimized factors for Analysis #{self.analysis.id}: {self.factors}"

class Suggestion(models.Model):
    analysis = models.ForeignKey(Analysis, on_delete=models.CASCADE)
    suggestion_text = models.TextField()

    def __str__(self):
        return f"Suggestion for Analysis #{self.analysis.id}: {self.suggestion_text}"

class ContactFormSubmission(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Contact Form Submission by {self.name} ({self.email})"

