from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.text import slugify

class AgeRange(models.Model):
    name = models.CharField(max_length=255, unique=True)
    min_age = models.PositiveIntegerField()
    max_age = models.PositiveIntegerField()
    slug = models.SlugField(max_length=255, unique=True, blank=True)

    class Meta:
        db_table = "age_range"
        verbose_name = "Age Range"
        verbose_name_plural = "Age Ranges"
        ordering = ["min_age"]

    def save(self, *args, **kwargs):
        if not self.slug or (self.pk and AgeRange.objects.get(pk=self.pk).name != self.name):
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while AgeRange.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class User(AbstractUser):
    GENDER_CHOICES = [
        ("male", "Male"),
        ("female", "Female"),
        ("other", "Other"),
    ]

    age_range = models.ForeignKey(
        AgeRange, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name="users"
    )
    registration_date = models.DateField(auto_now_add=True)
    city = models.CharField(max_length=255, blank=True, null=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, null=True)

    class Meta:
        db_table = "user"
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return self.username
