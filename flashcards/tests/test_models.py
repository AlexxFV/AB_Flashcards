import pytest
from django.contrib.auth import get_user_model
from flashcards.models import FlashCard, Collection, Rating, DailyLimit
from rest_framework.test import APIClient
from django.urls import reverse
from django.utils.timezone import now
from django.http import HttpResponseRedirect
import pytest
from django.contrib.auth import get_user_model
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST

User = get_user_model()

# Test: Create a user
@pytest.mark.django_db
def test_create_user():
    user = User.objects.create_user(username="testuser", password="Testpassword")
    assert user.username == "testuser"
    assert user.check_password("Testpassword")

# Test: Create a flashcard
@pytest.mark.django_db
def test_flashcard_api_create():
    user = User.objects.create_user(username="testuser", password="Testpassword")
    DailyLimit.objects.create(max_flashcards=20, max_collections=5)

    client = APIClient()
    client.login(username="testuser", password="Testpassword")

    url = reverse('flashcards:flashcard_create')
    data = {
        "question": "What is Python?",
        "answer": "A programming language",
        "difficulty": "easy"
    }

    response = client.post(url, data, follow=True) 

    assert response.status_code == 200, response.content

    flashcard = FlashCard.objects.filter(
        question="What is Python?",
        answer="A programming language",
        difficulty="easy",
        created_by=user
    ).first()
    assert flashcard is not None, "Flashcard was not created"
    assert flashcard.created_by == user

# Test: average rating
@pytest.mark.django_db
def test_flashcard_average_rating():
    user = User.objects.create_user(username="testuser", password="Testpassword")
    flashcard = FlashCard.objects.create(
        question="What is Django?",
        answer="A web framework",
        difficulty="medium",
        created_by=user,
    )
    Rating.objects.create(user=user, flashcard=flashcard, rating=4)
    rating = Rating.objects.get(user=user, flashcard=flashcard)
    rating.rating = 5
    rating.save()

    assert flashcard.average_rating == 5  

# Test: Create a collection
@pytest.mark.django_db
def test_create_collection():
    user = User.objects.create_user(username="testuser", password="Testpassword")
    flashcard = FlashCard.objects.create(
        question="What is pytest?",
        answer="A testing framework",
        difficulty="easy",
        created_by=user,
    )
    collection = Collection.objects.create(name="Testing Basics", user=user)
    collection.flashcards.add(flashcard)

    assert collection.name == "Testing Basics"
    assert collection.user == user
    assert collection.flashcards.count() == 1
    assert collection.flashcards.first() == flashcard

# Test: Daily limit
@pytest.mark.django_db
def test_daily_limit():
    limit = DailyLimit.objects.create(max_flashcards=10, max_collections=5)
    assert limit.max_flashcards == 10
    assert limit.max_collections == 5

# Test: hide flashcard
@pytest.mark.django_db
def test_hide_flashcard(client):
    user = User.objects.create_user(username="testuser", password="Testpassword")
    flashcard = FlashCard.objects.create(
        question="What is Python?",
        answer="A programming language",
        difficulty="easy",
        created_by=user
    )
    client.login(username="testuser", password="Testpassword")
    url = reverse('flashcards:flashcard_toggle_hidden', args=[flashcard.id])

    # Hide
    response = client.post(url)
    assert response.status_code == 200
    assert response.json()['hidden'] is True

    # Unhide
    response = client.post(url)
    assert response.status_code == 200
    assert response.json()['hidden'] is False


# Test: Rating
@pytest.mark.django_db
def test_rate_flashcard(client):
    user = User.objects.create_user(username="testuser", password="Testpassword")
    flashcard = FlashCard.objects.create(
        question="What is Django?",
        answer="A Python web framework",
        difficulty="medium",
        created_by=user,
    )
    client.login(username="testuser", password="Testpassword")
    url = reverse('flashcards:rate_flashcard', args=[flashcard.id])
    data = {"rating": 5}

    response = client.post(url, data, content_type="application/json")
    assert response.status_code == 200
    assert flashcard.average_rating == 5

# Test:Shared
@pytest.mark.django_db
def test_shared_flashcards_order(client):
    user = User.objects.create_user(username="testuser", password="Testpassword")
    flashcard1 = FlashCard.objects.create(
        question="What is Python?",
        answer="A programming language",
        difficulty="easy",
        is_shared=True,
        created_by=user
    )
    flashcard2 = FlashCard.objects.create(
        question="What is Django?",
        answer="A web framework",
        difficulty="medium",
        is_shared=True,
        created_by=user
    )
    Rating.objects.create(user=user, flashcard=flashcard1, rating=5)
    Rating.objects.create(user=user, flashcard=flashcard2, rating=3)

    client.login(username="testuser", password="Testpassword")
    url = reverse('flashcards:flashcard_shared_list')
    response = client.get(url)

    assert response.status_code == 200
    content = response.content.decode()
    assert content.index("What is Python?") < content.index("What is Django?")

@pytest.mark.django_db
def test_collection_serialization():
    user = User.objects.create_user(username="testuser", password="Testpassword")
    flashcard = FlashCard.objects.create(
        question="What is pytest?",
        answer="A testing framework",
        difficulty="easy",
        created_by=user,
    )
    collection = Collection.objects.create(name="Testing Basics", user=user)
    collection.flashcards.add(flashcard)

    client = APIClient()
    client.login(username="testuser", password="Testpassword")
    url = reverse('collection-detail', args=[collection.id])
    response = client.get(url)
    assert response.status_code == HTTP_200_OK

    data = response.json()
    assert data["name"] == "Testing Basics"
    assert len(data["flashcards"]) == 1
    assert data["flashcards"][0]["question"] == "What is pytest?"

# Tests: Delete flashcard
@pytest.mark.django_db
def test_flashcard_delete():
    user = User.objects.create_user(username="testuser", password="Testpassword")
    flashcard = FlashCard.objects.create(
        question="What is Django?",
        answer="A web framework",
        difficulty="medium",
        created_by=user,
    )

    client = APIClient()
    client.login(username="testuser", password="Testpassword")

    # Delete flashcard
    url = reverse('flashcards:flashcard_delete', args=[flashcard.id])
    response = client.post(url)

   
    assert response.status_code == 302
    assert isinstance(response, HttpResponseRedirect)
    assert response.url == reverse('flashcards:flashcard_list')
    assert not FlashCard.objects.filter(id=flashcard.id).exists()

# Tests: Study mode
@pytest.mark.django_db
def test_invalid_study_question_index():
    user = User.objects.create_user(username="testuser", password="Testpassword")
    collection = Collection.objects.create(name="Study Collection", user=user)

    client = APIClient()
    client.login(username="testuser", password="Testpassword")
    url = reverse('flashcards:study_question', args=[collection.id, 999])
    response = client.get(url)
    assert response.status_code == 302  # Redirect to results
