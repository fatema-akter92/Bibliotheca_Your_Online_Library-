from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing, name='landing'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),

    path('panel/', views.admin_dashboard, name='admin_dashboard'),
    path('panel/approve-member/<int:pk>/', views.approve_member, name='approve_member'),
    path('panel/reject-member/<int:pk>/', views.reject_member, name='reject_member'),
    path('panel/approve-borrow/<int:pk>/', views.approve_borrow, name='approve_borrow'),
    path('panel/reject-borrow/<int:pk>/', views.reject_borrow, name='reject_borrow'),
    path('panel/return/<int:pk>/', views.return_book, name='return_book'),
    path('panel/reservations/', views.admin_reservations, name='admin_reservations'),
    path('panel/reservations/issue/<int:pk>/', views.issue_reserved, name='issue_reserved'),
    path('panel/reservations/cancel/<int:pk>/', views.cancel_reservation_admin, name='cancel_reservation_admin'),
    path('panel/profile/', views.admin_profile, name='admin_profile'),

    path('books/', views.book_list, name='book_list'),
    path('books/add/', views.book_add, name='book_add'),
    path('books/<int:pk>/', views.book_detail, name='book_detail'),
    path('books/<int:pk>/edit/', views.book_edit, name='book_edit'),
    path('books/<int:pk>/delete/', views.book_delete, name='book_delete'),

    path('categories/', views.category_list, name='category_list'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),

    path('members/', views.member_list, name='member_list'),

    path('dashboard/', views.member_dashboard, name='member_dashboard'),
    path('browse/', views.member_books, name='member_books'),
    path('browse/<int:pk>/', views.member_book_detail, name='member_book_detail'),
    path('borrow/<int:book_pk>/', views.borrow_request, name='borrow_request'),
    path('return-request/<int:pk>/', views.member_return_request, name='member_return_request'),
    path('reserve/<int:book_pk>/', views.reserve_book, name='reserve_book'),
    path('reservations/', views.member_reservations, name='member_reservations'),
    path('reservations/cancel/<int:pk>/', views.cancel_reservation, name='cancel_reservation'),
    path('my-history/', views.member_history, name='member_history'),
    path('profile/', views.member_profile, name='member_profile'),
    path('my-categories/', views.member_category_list, name='member_category_list'),


    path('ai/', views.ai_recommender, name='ai_recommender'),
    path('analytics/', views.analytics, name='analytics'),
]