from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count
from django.db.models.functions import TruncMonth, TruncDay
from datetime import date, timedelta
import json
from .models import Book, Category, Member, BorrowRecord, Reservation


def is_admin(user):
    return user.is_staff or user.is_superuser

def get_member(user):
    try:
        return user.member_profile
    except:
        return None


# ── AUTH ──────────────────────────────────────────────────────────────────────

def landing(request):
    return render(request, 'library/landing.html')

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            if is_admin(user):
                return redirect('admin_dashboard')
            return redirect('member_dashboard')
        messages.error(request, 'Wrong username or password.')
    return render(request, 'library/login.html')

def logout_view(request):
    logout(request)
    return redirect('landing')

def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        password2 = request.POST.get('password2', '')
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        address = request.POST.get('address', '').strip()

        if password != password2:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'library/register.html')
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already taken.')
            return render(request, 'library/register.html')

        user = User.objects.create_user(
            username=username, email=email, password=password,
            first_name=first_name, last_name=last_name
        )
        Member.objects.create(user=user, phone=phone, address=address)
        login(request, user)
        messages.success(request, 'Account created! Browse books freely. Request membership to borrow.')
        return redirect('member_dashboard')
    return render(request, 'library/register.html')


# ── ADMIN DASHBOARD ───────────────────────────────────────────────────────────

@login_required
def admin_dashboard(request):
    if not is_admin(request.user):
        return redirect('member_dashboard')

    today = date.today()
    pending_members = Member.objects.filter(is_approved=False).select_related('user')
    pending_borrows = BorrowRecord.objects.filter(status='pending').select_related('member__user', 'book')
    active_borrows = BorrowRecord.objects.filter(status='approved').select_related('member__user', 'book')
    ready_reservations = Reservation.objects.filter(status='ready').select_related('member__user', 'book')

    for b in active_borrows:
        b.calculate_fine()

    week_ago = today - timedelta(days=6)
    daily_data = (
        BorrowRecord.objects
        .filter(request_date__date__gte=week_ago)
        .annotate(day=TruncDay('request_date'))
        .values('day')
        .annotate(count=Count('id'))
        .order_by('day')
    )
    day_map = {d['day'].date(): d['count'] for d in daily_data}
    weekly_data = json.dumps([
        {'day': (week_ago + timedelta(days=i)).strftime('%a'),
         'count': day_map.get(week_ago + timedelta(days=i), 0)}
        for i in range(7)
    ])

    cat_data = list(Category.objects.annotate(
        borrow_count=Count('books__borrow_records')
    ).order_by('-borrow_count')[:6])

    most_borrowed = Book.objects.annotate(
        times_borrowed=Count('borrow_records')
    ).order_by('-times_borrowed')[:5]

    recent_loans = BorrowRecord.objects.select_related('member__user', 'book').order_by('-request_date')[:8]

    return render(request, 'library/admin_dashboard.html', {
        'pending_members': pending_members,
        'pending_borrows': pending_borrows,
        'active_borrows': active_borrows,
        'ready_reservations': ready_reservations,
        'total_books': Book.objects.count(),
        'total_members': Member.objects.filter(is_approved=True).count(),
        'total_pending_members': pending_members.count(),
        'total_pending_borrows': pending_borrows.count(),
        'today': today,
        'overdue_count': BorrowRecord.objects.filter(status='approved', due_date__lt=today).count(),
        'issued_today': BorrowRecord.objects.filter(issue_date=today).count(),
        'returned_today': BorrowRecord.objects.filter(return_date=today).count(),
        'weekly_data': weekly_data,
        'cat_data': cat_data,
        'most_borrowed': most_borrowed,
        'recent_loans': recent_loans,
        'available_books': Book.objects.filter(available_copies__gt=0).count(),
    })


@login_required
def approve_member(request, pk):
    if not is_admin(request.user): return redirect('member_dashboard')
    member = get_object_or_404(Member, pk=pk)
    member.is_approved = True
    member.save()
    messages.success(request, f'"{member}" approved!')
    return redirect('admin_dashboard')

@login_required
def reject_member(request, pk):
    if not is_admin(request.user): return redirect('member_dashboard')
    member = get_object_or_404(Member, pk=pk)
    member.user.delete()
    messages.success(request, 'Member rejected and removed.')
    return redirect('admin_dashboard')

@login_required
def approve_borrow(request, pk):
    if not is_admin(request.user): return redirect('member_dashboard')
    record = get_object_or_404(BorrowRecord, pk=pk)
    if record.book.available_copies < 1:
        messages.error(request, 'No copies available!')
        return redirect('admin_dashboard')
    record.status = 'approved'
    record.issue_date = date.today()
    record.due_date = date.today() + timedelta(days=14)
    record.save()
    record.book.available_copies -= 1
    record.book.save()
    messages.success(request, f'Borrow approved for {record.member}!')
    return redirect('admin_dashboard')

@login_required
def reject_borrow(request, pk):
    if not is_admin(request.user): return redirect('member_dashboard')
    record = get_object_or_404(BorrowRecord, pk=pk)
    record.status = 'rejected'
    record.save()
    messages.success(request, 'Borrow request rejected.')
    return redirect('admin_dashboard')

@login_required
def return_book(request, pk):
    if not is_admin(request.user): return redirect('member_dashboard')
    record = get_object_or_404(BorrowRecord, pk=pk)
    record.status = 'returned'
    record.return_date = date.today()
    record.calculate_fine()
    record.save()
    record.book.available_copies += 1
    record.book.save()

    next_res = Reservation.objects.filter(
        book=record.book, status='waiting'
    ).order_by('reserved_date').first()
    if next_res:
        next_res.status = 'ready'
        next_res.notified = True
        next_res.save()
        messages.success(request, f'Book returned. Reservation for "{next_res.member}" is now ready!')
    else:
        messages.success(request, f'Book returned by {record.member}.')
    return redirect('admin_dashboard')


# ── RESERVATIONS (Admin) ──────────────────────────────────────────────────────

@login_required
def admin_reservations(request):
    if not is_admin(request.user): return redirect('member_dashboard')
    all_reservations = Reservation.objects.select_related('member__user', 'book').order_by('-reserved_date')
    return render(request, 'library/admin_reservations.html', {
        'all_reservations': all_reservations,
        'waiting_count': all_reservations.filter(status='waiting').count(),
        'ready_count': all_reservations.filter(status='ready').count(),
    })

@login_required
def issue_reserved(request, pk):
    if not is_admin(request.user): return redirect('member_dashboard')
    res = get_object_or_404(Reservation, pk=pk)
    if res.book.available_copies < 1:
        messages.error(request, 'No copies available yet!')
        return redirect('admin_reservations')
    BorrowRecord.objects.create(
        member=res.member, book=res.book,
        status='approved', issue_date=date.today(),
        due_date=date.today() + timedelta(days=14),
    )
    res.book.available_copies -= 1
    res.book.save()
    res.status = 'issued'
    res.save()
    messages.success(request, f'Book issued to {res.member} from reservation!')
    return redirect('admin_reservations')

@login_required
def cancel_reservation_admin(request, pk):
    if not is_admin(request.user): return redirect('member_dashboard')
    res = get_object_or_404(Reservation, pk=pk)
    res.status = 'cancelled'
    res.save()
    messages.success(request, 'Reservation cancelled.')
    return redirect('admin_reservations')


# ── BOOKS ─────────────────────────────────────────────────────────────────────

@login_required
def book_list(request):
    if not is_admin(request.user): return redirect('member_books')
    category_id = request.GET.get('category')
    search = request.GET.get('search', '')
    books = Book.objects.select_related('category').all()
    if category_id:
        books = books.filter(category_id=category_id)
    if search:
        books = books.filter(title__icontains=search) | books.filter(author__icontains=search)
    return render(request, 'library/book_list.html', {
        'books': books,
        'categories': Category.objects.all(),
        'selected_category': category_id,
        'search': search,
    })

@login_required
def book_add(request):
    if not is_admin(request.user): return redirect('member_dashboard')
    if request.method == 'POST':
        copies = int(request.POST.get('total_copies', 1))
        Book.objects.create(
            title=request.POST.get('title', '').strip(),
            author=request.POST.get('author', '').strip(),
            category_id=request.POST.get('category') or None,
            isbn=request.POST.get('isbn', '').strip(),
            total_copies=copies,
            available_copies=copies,
            description=request.POST.get('description', '').strip(),
        )
        messages.success(request, 'Book added!')
        return redirect('book_list')
    return render(request, 'library/book_form.html', {
        'categories': Category.objects.all(),
        'action': 'Add'
    })

@login_required
def book_edit(request, pk):
    if not is_admin(request.user): return redirect('member_dashboard')
    book = get_object_or_404(Book, pk=pk)
    if request.method == 'POST':
        book.title = request.POST.get('title', '').strip()
        book.author = request.POST.get('author', '').strip()
        book.category_id = request.POST.get('category') or None
        book.isbn = request.POST.get('isbn', '').strip()
        book.total_copies = int(request.POST.get('total_copies', 1))
        book.description = request.POST.get('description', '').strip()
        book.save()
        messages.success(request, 'Book updated!')
        return redirect('book_list')
    return render(request, 'library/book_form.html', {
        'book': book,
        'categories': Category.objects.all(),
        'action': 'Edit'
    })

@login_required
def book_delete(request, pk):
    if not is_admin(request.user): return redirect('member_dashboard')
    book = get_object_or_404(Book, pk=pk)
    book.delete()
    messages.success(request, f'"{book.title}" deleted.')
    return redirect('book_list')

@login_required
def book_detail(request, pk):
    if not is_admin(request.user): return redirect('member_dashboard')
    book = get_object_or_404(Book, pk=pk)
    return render(request, 'library/book_detail.html', {'book': book})

@login_required
def member_book_detail(request, pk):
    member = get_member(request.user)
    if not member: return redirect('landing')
    book = get_object_or_404(Book, pk=pk)
    already_borrowed = BorrowRecord.objects.filter(
        member=member, book=book, status__in=['pending', 'approved']
    ).exists()
    already_reserved = Reservation.objects.filter(
        member=member, book=book, status__in=['waiting', 'ready']
    ).exists()
    return render(request, 'library/member_book_detail.html', {
        'book': book,
        'member': member,
        'already_borrowed': already_borrowed,
        'already_reserved': already_reserved,
    })


# ── CATEGORIES ────────────────────────────────────────────────────────────────

@login_required
def category_list(request):
    if not is_admin(request.user): return redirect('member_dashboard')
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        desc = request.POST.get('description', '').strip()
        if name:
            Category.objects.create(name=name, description=desc)
            messages.success(request, f'Category "{name}" added!')
    categories = Category.objects.annotate(book_count=Count('books'))
    return render(request, 'library/category_list.html', {'categories': categories})

@login_required
def category_delete(request, pk):
    if not is_admin(request.user): return redirect('member_dashboard')
    cat = get_object_or_404(Category, pk=pk)
    cat.delete()
    messages.success(request, 'Category deleted.')
    return redirect('category_list')


# ── MEMBER VIEWS ──────────────────────────────────────────────────────────────

@login_required
def member_dashboard(request):
    if is_admin(request.user): return redirect('admin_dashboard')
    member = get_member(request.user)
    if not member: return redirect('landing')

    today = date.today()
    active_borrows = BorrowRecord.objects.filter(member=member, status='approved').select_related('book')
    pending_requests = BorrowRecord.objects.filter(member=member, status='pending').select_related('book')
    my_reservations = Reservation.objects.filter(member=member, status__in=['waiting', 'ready']).select_related('book')
    history = BorrowRecord.objects.filter(
        member=member, status__in=['returned', 'rejected']
    ).select_related('book').order_by('-request_date')[:5]

    for b in active_borrows:
        b.calculate_fine()

    week_ago = today - timedelta(days=6)
    daily_data = (
        BorrowRecord.objects
        .filter(member=member, request_date__date__gte=week_ago)
        .annotate(day=TruncDay('request_date'))
        .values('day')
        .annotate(count=Count('id'))
        .order_by('day')
    )
    day_map = {d['day'].date(): d['count'] for d in daily_data}
    weekly_data = json.dumps([
        {'day': (week_ago + timedelta(days=i)).strftime('%a'),
         'count': day_map.get(week_ago + timedelta(days=i), 0)}
        for i in range(7)
    ])

    total_borrowed = BorrowRecord.objects.filter(member=member, status__in=['approved', 'returned']).count()
    total_returned = BorrowRecord.objects.filter(member=member, status='returned').count()
    total_fines = sum(b.fine for b in active_borrows)

    cat_data = list(Category.objects.filter(
        books__borrow_records__member=member
    ).annotate(borrow_count=Count('books__borrow_records')).order_by('-borrow_count')[:5])

    recent_loans = BorrowRecord.objects.filter(member=member).select_related('book').order_by('-request_date')[:8]

    return render(request, 'library/member_dashboard.html', {
        'member': member,
        'active_borrows': active_borrows,
        'pending_requests': pending_requests,
        'my_reservations': my_reservations,
        'history': history,
        'today': today,
        'weekly_data': weekly_data,
        'total_borrowed': total_borrowed,
        'total_returned': total_returned,
        'total_fines': total_fines,
        'cat_data': cat_data,
        'recent_loans': recent_loans,
        'total_books': Book.objects.count(),
        'available_books': Book.objects.filter(available_copies__gt=0).count(),
        'total_categories': Category.objects.count(),
    })


@login_required
def member_books(request):
    if is_admin(request.user): return redirect('book_list')
    member = get_member(request.user)
    if not member: return redirect('landing')

    category_id = request.GET.get('category')
    search = request.GET.get('search', '')
    books = Book.objects.select_related('category').all()
    if category_id:
        books = books.filter(category_id=category_id)
    if search:
        books = books.filter(title__icontains=search) | books.filter(author__icontains=search)

    member_borrow_requests = []
    member_reserved_books = []
    if member.is_approved:
        member_borrow_requests = list(BorrowRecord.objects.filter(
            member=member, status__in=['pending', 'approved']
        ).values_list('book_id', flat=True))
        member_reserved_books = list(Reservation.objects.filter(
            member=member, status__in=['waiting', 'ready']
        ).values_list('book_id', flat=True))

    categories = Category.objects.all()
    categories_with_books = []
    for cat in categories:
        cat_books = list(Book.objects.filter(category=cat))
        if cat_books:
            cat.book_list = cat_books
            categories_with_books.append(cat)
    uncategorized_books = list(Book.objects.filter(category=None))

    return render(request, 'library/member_books.html', {
        'books': books,
        'categories': categories,
        'categories_with_books': categories_with_books,
        'uncategorized_books': uncategorized_books,
        'selected_category': category_id,
        'search': search,
        'member_borrow_requests': member_borrow_requests,
        'member_reserved_books': member_reserved_books,
        'member': member,
        'total_books': Book.objects.count(),
        'available_books': Book.objects.filter(available_copies__gt=0).count(),
    })


@login_required
def borrow_request(request, book_pk):
    member = get_member(request.user)
    if not member: return redirect('landing')
    if not member.is_approved:
        messages.error(request, 'Your membership is not approved yet.')
        return redirect('member_books')
    book = get_object_or_404(Book, pk=book_pk)
    if BorrowRecord.objects.filter(member=member, book=book, status__in=['pending', 'approved']).exists():
        messages.warning(request, 'You already have an active request for this book.')
        return redirect('member_books')
    if not book.is_available:
        messages.error(request, 'This book is not available. You can reserve it instead.')
        return redirect('member_books')
    BorrowRecord.objects.create(member=member, book=book)
    messages.success(request, f'Borrow request sent for "{book.title}"!')
    return redirect('member_dashboard')


@login_required
def member_return_request(request, pk):
    member = get_member(request.user)
    if not member: return redirect('landing')
    record = get_object_or_404(BorrowRecord, pk=pk, member=member, status='approved')
    record.status = 'return_requested'
    record.save()
    messages.success(request, f'Return request sent for "{record.book.title}". Admin will process it.')
    return redirect('member_dashboard')

@login_required
def member_category_list(request):
    if is_admin(request.user): return redirect('category_list')
    member = get_member(request.user)
    categories = Category.objects.annotate(book_count=Count('books')).order_by('name')
    selected_cat = request.GET.get('cat')
    selected_category = None
    category_books = []
    if selected_cat:
        selected_category = get_object_or_404(Category, pk=selected_cat)
        category_books = Book.objects.filter(category=selected_category).select_related('author')
    member_borrow_requests = []
    member_reserved_books = []
    if member and member.is_approved:
        member_borrow_requests = list(BorrowRecord.objects.filter(
            member=member, status__in=['pending', 'approved']
        ).values_list('book_id', flat=True))
        member_reserved_books = list(Reservation.objects.filter(
            member=member, status__in=['waiting', 'ready']
        ).values_list('book_id', flat=True))
    return render(request, 'library/member_category_list.html', {
        'categories': categories,
        'selected_category': selected_category,
        'category_books': category_books,
        'member': member,
        'member_borrow_requests': member_borrow_requests,
        'member_reserved_books': member_reserved_books,
    })

@login_required
def reserve_book(request, book_pk):
    member = get_member(request.user)
    if not member: return redirect('landing')
    if not member.is_approved:
        messages.error(request, 'Your membership is not approved yet.')
        return redirect('member_books')
    book = get_object_or_404(Book, pk=book_pk)
    if Reservation.objects.filter(member=member, book=book, status__in=['waiting', 'ready']).exists():
        messages.warning(request, 'You already have a reservation for this book.')
        return redirect('member_books')
    if book.is_available:
        messages.info(request, 'This book is available — you can borrow it directly!')
        return redirect('member_books')
    Reservation.objects.create(member=member, book=book)
    messages.success(request, f'Reserved "{book.title}"! You will be notified when it\'s ready.')
    return redirect('member_reservations')


@login_required
def cancel_reservation(request, pk):
    member = get_member(request.user)
    if not member: return redirect('landing')
    res = get_object_or_404(Reservation, pk=pk, member=member)
    res.status = 'cancelled'
    res.save()
    messages.success(request, 'Reservation cancelled.')
    return redirect('member_reservations')


@login_required
def member_reservations(request):
    member = get_member(request.user)
    if not member: return redirect('landing')

    search_query = request.GET.get('q', '').strip()
    search_results = []
    already_borrowed = []

    if search_query:
        search_results = list(Book.objects.filter(
            title__icontains=search_query
        ).select_related('category', 'author') | Book.objects.filter(
            author__name__icontains=search_query
        ).select_related('category', 'author'))
        # Remove duplicates
        seen = set()
        unique_results = []
        for book in search_results:
            if book.pk not in seen:
                seen.add(book.pk)
                unique_results.append(book)
        search_results = unique_results

        already_borrowed = list(BorrowRecord.objects.filter(
            member=member, status__in=['pending', 'approved']
        ).values_list('book_id', flat=True))

    reservations = Reservation.objects.filter(member=member).select_related('book').order_by('-reserved_date')
    already_reserved = list(Reservation.objects.filter(
        member=member, status__in=['waiting', 'ready']
    ).values_list('book_id', flat=True))

    return render(request, 'library/member_reservations.html', {
        'reservations': reservations,
        'member': member,
        'search_query': search_query,
        'search_results': search_results,
        'already_reserved': already_reserved,
        'already_borrowed': already_borrowed,
    })


@login_required
def member_history(request):
    member = get_member(request.user)
    if not member: return redirect('landing')
    records = BorrowRecord.objects.filter(member=member).select_related('book').order_by('-request_date')
    return render(request, 'library/member_history.html', {'records': records, 'member': member})


@login_required
def member_list(request):
    if not is_admin(request.user): return redirect('member_dashboard')
    members = Member.objects.filter(is_approved=True).select_related('user').annotate(
        total_borrows=Count('borrow_records')
    )
    return render(request, 'library/member_list.html', {'members': members})


# ── PROFILES ──────────────────────────────────────────────────────────────────

@login_required
def member_profile(request):
    if is_admin(request.user): return redirect('admin_profile')
    member = get_member(request.user)
    if not member: return redirect('landing')
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name', '').strip()
        user.last_name = request.POST.get('last_name', '').strip()
        user.email = request.POST.get('email', '').strip()
        user.save()
        member.phone = request.POST.get('phone', '').strip()
        member.address = request.POST.get('address', '').strip()
        member.save()
        messages.success(request, 'Profile updated!')
        return redirect('member_profile')
    all_borrows = BorrowRecord.objects.filter(member=member).select_related('book').order_by('-request_date')
    total_borrowed = all_borrows.filter(status__in=['approved', 'returned']).count()
    total_returned = all_borrows.filter(status='returned').count()
    active_borrows = all_borrows.filter(status='approved')
    total_fines = sum(b.fine for b in active_borrows)
    reservations = Reservation.objects.filter(member=member).select_related('book').order_by('-reserved_date')[:5]
    return render(request, 'library/member_profile.html', {
        'member': member,
        'all_borrows': all_borrows[:10],
        'total_borrowed': total_borrowed,
        'total_returned': total_returned,
        'total_fines': total_fines,
        'active_borrows': active_borrows,
        'reservations': reservations,
        'today': date.today(),
    })


@login_required
def admin_profile(request):
    if not is_admin(request.user): return redirect('member_profile')
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name', '').strip()
        user.last_name = request.POST.get('last_name', '').strip()
        user.email = request.POST.get('email', '').strip()
        user.save()
        messages.success(request, 'Profile updated!')
        return redirect('admin_profile')
    today = date.today()
    return render(request, 'library/admin_profile.html', {
        'total_books': Book.objects.count(),
        'total_members': Member.objects.filter(is_approved=True).count(),
        'total_borrows': BorrowRecord.objects.filter(status__in=['approved', 'returned']).count(),
        'total_returned': BorrowRecord.objects.filter(status='returned').count(),
        'pending_members': Member.objects.filter(is_approved=False).count(),
        'overdue': BorrowRecord.objects.filter(status='approved', due_date__lt=today).count(),
        'today': today,
    })


# ── AI RECOMMENDER ────────────────────────────────────────────────────────────

@login_required
def ai_recommender(request):
    member = get_member(request.user)
    recommendation = None
    if request.method == 'POST':
        prompt = request.POST.get('prompt', '').strip()
        if prompt:
            try:
                from google import genai
                from django.conf import settings
                client = genai.Client(api_key=settings.GEMINI_API_KEY)
                books = Book.objects.select_related('category').all()[:60]
                book_str = "\n".join([
                    f"- {b.title} by {b.author if b.author else 'Unknown'}"
                    f" ({b.category.name if b.category else 'Uncategorized'})"
                    f" — {'Available' if b.is_available else 'Unavailable'}"
                    for b in books
                ])
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=f"""You are a friendly library assistant for Bibliotheca.
Our collection:
{book_str}

User request: {prompt}

Recommend 3-5 books from our collection and briefly explain why. Be warm and concise."""
                )
                recommendation = response.text
            except Exception as e:
                messages.error(request, f'AI error: {str(e)}')

    return render(request, 'library/ai_recommender.html', {
        'recommendation': recommendation,
        'member': member,
    })

# ── ANALYTICS ─────────────────────────────────────────────────────────────────

@login_required
def analytics(request):
    cat_data = list(Category.objects.annotate(book_count=Count('books')).values('name', 'book_count'))
    monthly_data = (
        BorrowRecord.objects
        .annotate(month=TruncMonth('request_date'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )
    return render(request, 'library/analytics.html', {
        'total_books': Book.objects.count(),
        'total_members': Member.objects.filter(is_approved=True).count(),
        'total_borrows': BorrowRecord.objects.filter(status__in=['approved', 'returned']).count(),
        'total_returned': BorrowRecord.objects.filter(status='returned').count(),
        'total_reservations': Reservation.objects.filter(status__in=['waiting', 'ready']).count(),
        'cat_labels': json.dumps([c['name'] for c in cat_data]),
        'cat_values': json.dumps([c['book_count'] for c in cat_data]),
        'monthly_labels': json.dumps([m['month'].strftime('%b %Y') for m in monthly_data]),
        'monthly_values': json.dumps([m['count'] for m in monthly_data]),
        'member': get_member(request.user),
    })