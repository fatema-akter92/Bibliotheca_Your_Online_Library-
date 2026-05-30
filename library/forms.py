from django import forms
from django.utils import timezone
from datetime import timedelta
from .models import Book, Member, Loan, Reservation, Genre, Author
from django.conf import settings


class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = ['isbn', 'title', 'authors', 'genre', 'publisher', 'publish_year',
                  'description', 'total_copies', 'available_copies', 'cover_color']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'cover_color': forms.TextInput(attrs={'type': 'color'}),
            'authors': forms.SelectMultiple(attrs={'size': 1}),
        }


class MemberForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = ['first_name', 'last_name', 'email', 'phone', 'address',
                  'status', 'membership_expiry', 'avatar_color']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 2}),
            'membership_expiry': forms.DateInput(attrs={'type': 'date'}),
            'avatar_color': forms.TextInput(attrs={'type': 'color'}),
        }


class LoanForm(forms.Form):
    book = forms.ModelChoiceField(
        queryset=Book.objects.filter(status='available'),
        label='Select Book',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    member = forms.ModelChoiceField(
        queryset=Member.objects.filter(status='active'),
        label='Select Member',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    loan_days = forms.IntegerField(
        min_value=1, max_value=60,
        initial=settings.DEFAULT_LOAN_DAYS,
        label='Loan Duration (days)',
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 2, 'class': 'form-control'})
    )


class ReturnForm(forms.Form):
    loan_id = forms.IntegerField(widget=forms.HiddenInput())
    collect_fine = forms.BooleanField(required=False, label='Collect fine now')


class ReservationForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = ['book', 'member', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 2}),
        }


class BookSearchForm(forms.Form):
    query = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Search by title, author, ISBN...', 'class': 'form-control'})
    )
    genre = forms.ModelChoiceField(
        queryset=Genre.objects.all(),
        required=False,
        empty_label='All Genres',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    status = forms.ChoiceField(
        choices=[('', 'All Status')] + Book.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class MemberSearchForm(forms.Form):
    query = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Search by name, email, member ID...', 'class': 'form-control'})
    )
    status = forms.ChoiceField(
        choices=[('', 'All Status')] + Member.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )