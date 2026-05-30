from django.contrib import admin
from .models import Category, Book, Member, BorrowRecord, Reservation

admin.site.register(Category)
admin.site.register(Book)
admin.site.register(Member)
admin.site.register(BorrowRecord)
admin.site.register(Reservation)