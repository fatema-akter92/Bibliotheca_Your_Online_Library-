from django.utils import timezone
from .models import Loan
from django.conf import settings


def update_overdue_loans():
    """Mark all past-due active loans as overdue and calculate fines."""
    today = timezone.now().date()
    active_loans = Loan.objects.filter(status__in=['active', 'overdue'])
    for loan in active_loans:
        if loan.due_date < today:
            loan.status = 'overdue'
            loan.fine_amount = (today - loan.due_date).days * settings.FINE_PER_DAY
            loan.save()


def get_ai_recommendations(prompt, reading_history=None):
    """Call Anthropic API for book recommendations."""
    try:
        import anthropic
        from django.conf import settings

        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        system_prompt = """You are Bibliotheca's expert AI librarian. 
        Given a member's reading history or a prompt, recommend 5 books with brief, 
        enthusiastic explanations. Format your response as a numbered list with book title 
        in bold, author, and a 1-2 sentence reason. Be warm, knowledgeable, and specific."""

        history_context = ""
        if reading_history:
            history_context = f"\nMember's recent reading history: {', '.join(reading_history)}"

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": f"{prompt}{history_context}"
                }
            ],
            system=system_prompt
        )
        return message.content[0].text
    except Exception as e:
        return f"Unable to get recommendations at this time: {str(e)}"


def get_dashboard_stats():
    """Compute all dashboard statistics."""
    from .models import Book, Member, Loan, Reservation
    today = timezone.now().date()

    total_books = Book.objects.aggregate(total=__import__('django.db.models', fromlist=['Sum']).Sum('total_copies'))['total'] or 0
    total_members = Member.objects.count()
    active_loans = Loan.objects.filter(status__in=['active', 'overdue']).count()
    overdue_count = Loan.objects.filter(status='overdue').count()
    issued_today = Loan.objects.filter(issue_date=today).count()
    returned_today = Loan.objects.filter(return_date=today).count()
    pending_reservations = Reservation.objects.filter(status='pending').count()

    return {
        'total_books': total_books,
        'total_members': total_members,
        'active_loans': active_loans,
        'overdue_count': overdue_count,
        'issued_today': issued_today,
        'returned_today': returned_today,
        'pending_reservations': pending_reservations,
    }