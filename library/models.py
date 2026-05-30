from django.db import models
from django.contrib.auth.models import User
from datetime import date


class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        return self.name


class Book(models.Model):
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=200, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='books')
    isbn = models.CharField(max_length=20, blank=True)
    total_copies = models.IntegerField(default=1)
    available_copies = models.IntegerField(default=1)
    description = models.TextField(blank=True)
    added_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.title

    @property
    def is_available(self):
        return self.available_copies > 0


class Member(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='member_profile')
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    is_approved = models.BooleanField(default=False)
    joined_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class BorrowRecord(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('return_requested', 'Return Requested'),
        ('returned', 'Returned'),
        ('rejected', 'Rejected'),
    ]
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='borrow_records')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='borrow_records')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    request_date = models.DateTimeField(auto_now_add=True)
    issue_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    return_date = models.DateField(null=True, blank=True)
    fine = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.member} → {self.book.title} [{self.status}]"

    def calculate_fine(self):
        if self.status in ['approved', 'return_requested'] and self.due_date:
            overdue = (date.today() - self.due_date).days
            if overdue > 0:
                self.fine = overdue * 5
                self.save()
        return self.fine


class Reservation(models.Model):
    STATUS_CHOICES = [
        ('waiting', 'Waiting'),
        ('ready', 'Ready for Pickup'),
        ('cancelled', 'Cancelled'),
        ('issued', 'Issued'),
    ]
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='reservations')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='reservations')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='waiting')
    reserved_date = models.DateTimeField(auto_now_add=True)
    notified = models.BooleanField(default=False)

    class Meta:
        ordering = ['reserved_date']

    def __str__(self):
        return f"{self.member} → {self.book.title} [{self.status}]"