"""
URL Configuration for Audiobooks API
"""
from django.urls import path
from .views import (
    BookUploadView,
    BookListView,
    MyBooksView,
    BookDetailView,
    BookPagesView,
    UpdateProgressView,
    MyLibraryView,
    LibraryAddView,
    LibraryRemoveView,
    ToggleFavoriteView,
    MyProgressView,
)

urlpatterns = [
    # Book Management
    path('upload/', BookUploadView.as_view(), name='book-upload'),
    path('books/', BookListView.as_view(), name='book-list'),
    path('my/', MyBooksView.as_view(), name='my-books'),
    path('<int:book_id>/', BookDetailView.as_view(), name='book-detail'),
    path('<int:book_id>/pages/', BookPagesView.as_view(), name='book-pages'),

    # Progress Tracking
    path('<int:book_id>/progress/', UpdateProgressView.as_view(), name='book-progress'),
    path('progress/', MyProgressView.as_view(), name='my-progress'),

    # Library Management
    path('library/', MyLibraryView.as_view(), name='my-library'),
    path('library/add/', LibraryAddView.as_view(), name='library-add'),
    path('library/<int:book_id>/', LibraryRemoveView.as_view(), name='library-remove'),
    path('library/<int:book_id>/favorite/', ToggleFavoriteView.as_view(), name='toggle-favorite'),
]
