import datetime
import json

from multipledispatch import dispatch

from django.utils import timezone
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase
from django.core.serializers.json import DjangoJSONEncoder

from rest_framework import status
from rest_framework.test import APITestCase

from .models import Question


def create_question(author, question_text, choices, days):
    """
    Create a question with the given `author`, `question_text`, `choices` and
    publishing date given number of `days` offset to now
    (negative for questions published in the past, positive
    for questions that are yet to be published).
    """

    date_published = timezone.now() + datetime.timedelta(days=days)

    return Question.objects.create(
        author=author,
        question_text=question_text,
        date_published=date_published,
        choices=choices,
    )


def create_question_data(question_text, choices, days=-1):
    """
    Create data to be sent via POST to create a new question with the given
    `question_text`, `choices` and publishing date given number of `days`
    offset to now (negative for questions published in the past, positive
    for questions that are yet to be published).
    """

    date_published = timezone.now() + datetime.timedelta(days=days)

    return json.dumps(
        {
            "question_text": question_text,
            "date_published": date_published,
            "choices": choices,
        },
        cls=DjangoJSONEncoder,
    )


def create_vote_data(hide_voter=True, choice=None):
    data = dict()
    if choice:
        data["choice"] = choice
    data["hide_voter"] = hide_voter

    return json.dumps(data, cls=DjangoJSONEncoder)


def create_choices_data(*args):
    return [{"choice_text": arg} for arg in args]


class QuestionModelTests(TestCase):
    def test_model_content(self):
        user = get_user_model().objects.create_user(
            username="testuser", email="test@email.com", password="secret"
        )
        question_text = "Question text"
        choices = create_choices_data("First choice", "Second choice", "Third choice")

        question = create_question(user, question_text, choices, days=-30)

        self.assertEqual(question.question_text, question_text)
        self.assertEqual(question.author.username, "testuser")
        self.assertEqual(question.get_absolute_url(), "/api/v1/polls/1/")
        self.assertEqual(question.choices.count(), 3)
        self.assertEqual(
            question.choices.get(choice_text="First choice").get_absolute_url(),
            "/api/v1/polls/1/choices/1/",
        )


class QuestionAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = cls.create_user("testuser", "secret")
        cls.question_text = "Question text"
        cls.choices = create_choices_data("First choice", "Second choice")

        cls.question_data = create_question_data(cls.question_text, cls.choices)

    @classmethod
    def create_user(self, username, password):
        return get_user_model().objects.create_user(
            username=username, password=password
        )

    # Test helpers
    ## paths
    @dispatch()
    def get_path(self):
        return reverse("polls:question-list")

    @dispatch(int)
    def get_path(self, question_id, choices=False):
        path = "polls:question-choice-list" if choices else "polls:question-detail"
        return reverse(path, args=(question_id,))

    @dispatch(int, int)
    def get_path(self, question_id, choice_id, votes=False):
        path = (
            "polls:question-choice-vote-list"
            if votes
            else "polls:question-choice-detail"
        )
        return reverse(path, args=(question_id, choice_id))

    @dispatch(int, int, int)
    def get_path(self, question_id, choice_id, vote_id):
        return reverse(
            "polls:question-choice-vote-detail", args=(question_id, choice_id, vote_id)
        )

    ## /api-auth/login/
    @dispatch()
    def login(self):
        self.login(self.user.username, "secret")

    @dispatch(str, str)
    def login(self, username, password):
        self.assertTrue(self.client.login(username=username, password=password))

    def create_user_and_login(self, username, password):
        user = self.create_user(username, password)
        self.login(username, password)
        return user

    ## /api-auth/logout/
    def logout(self):
        self.client.logout()

    ## GET /api/v1/polls/
    def get_questions(self):
        return self.client.get(self.get_path())

    def login_then_get_questions(self):
        self.login()
        return self.get_questions()

    ## POST /api/v1/polls/
    def post_question(self, data):
        return self.client.post(
            self.get_path(),
            data,
            content_type="application/json",
        )

    def login_then_post_question(self, data):
        self.login()
        return self.post_question(data)

    ## GET /api/v1/polls/{id}/
    def get_question(self, question_id):
        return self.client.get(self.get_path(question_id))

    def login_then_get_question(self, question_id):
        self.login()
        return self.get_question(question_id)

    ## DELETE /api/v1/polls/{id}/
    def delete_question(self, question_id):
        return self.client.delete(self.get_path(question_id))

    def login_then_delete_question(self, question_id):
        self.login()
        return self.delete_question(question_id)

    ## GET /api/v1/polls/{id}/choices/
    def get_choices(self, question_id):
        return self.client.get(self.get_path(question_id, choices=True))

    def login_then_get_choices(self, question_id):
        self.login()
        return self.get_question(question_id, choices=True)

    ## GET /api/v1/polls/{id}/choices/{id}/
    def get_choice(self, question_id, choice_id):
        return self.client.get(self.get_path(question_id, choice_id))

    def login_then_get_choice(self, question_id, choice_id):
        self.login()
        return self.get_question(question_id, choice_id)

    ## GET /api/v1/polls/{id}/choices/{id}/votes/
    def get_votes(self, question_id, choice_id):
        return self.client.get(self.get_path(question_id, choice_id, votes=True))

    def login_then_get_votes(self, question_id, choice_id):
        self.login()
        return self.get_votes(question_id, choice_id)

    ## POST /api/v1/polls/{id}/choices/{id}/votes/
    def post_vote(self, question_id, choice_id, data=None):
        return self.client.post(
            self.get_path(question_id, choice_id, votes=True),
            data,
            content_type="application/json",
        )

    def login_then_post_vote(self, question_id, choice_id, data=None):
        self.login()
        return self.post_vote(question_id, choice_id, data)

    ## GET /api/v1/polls/{id}/choices/{id}/votes/{id}/
    def get_vote(self, question_id, choice_id, vote_id):
        return self.client.get(self.get_path(question_id, choice_id, vote_id))

    def login_then_get_vote(self, question_id, choice_id, vote_id):
        self.login()
        return self.get_vote(question_id, choice_id, vote_id)

    ## DELETE /api/v1/polls/{id}/choices/{id}/votes/{id}/
    def delete_vote(self, question_id, choice_id, vote_id):
        return self.client.delete(self.get_path(question_id, choice_id, vote_id))

    def login_then_delete_vote(self, question_id, choice_id, vote_id):
        self.login()
        return self.delete_vote(question_id, choice_id, vote_id)

    ## PUT /api/v1/polls/{id}/choices/{id}/votes/{id}/
    def put_vote(self, question_id, choice_id, vote_id, data=None):
        return self.client.put(
            self.get_path(question_id, choice_id, vote_id),
            data,
            content_type="application/json",
        )

    def login_then_put_vote(self, question_id, choice_id, vote_id, data=None):
        self.login()
        return self.put_vote(question_id, choice_id, vote_id, data)

    # Tests
    ## GET /api/v1/polls/
    def test_unauthenticated_user_get_questions(self):
        response = self.get_questions()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_user_get_questions(self):
        response = self.login_then_get_questions()
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_no_questions(self):
        self.assertContains(self.login_then_get_questions(), "[]")

    def test_past_question(self):
        self.login_then_post_question(
            create_question_data("Past question", self.choices, days=-30)
        )
        self.assertContains(self.get_questions(), "Past question")

    def test_two_past_questions(self):
        self.login()
        self.post_question(
            create_question_data("Past question", self.choices, days=-30)
        )
        self.post_question(
            create_question_data("Another past question", self.choices, days=-1)
        )
        response = self.get_questions()
        self.assertContains(response, "Past question")
        self.assertContains(response, "Another past question")

    def test_future_and_past_questions(self):
        self.login()
        self.post_question(
            create_question_data("Past question", self.choices, days=-30)
        )
        self.post_question(
            create_question_data("Future question", self.choices, days=30)
        )
        response = self.get_questions()
        self.assertContains(response, "Past question")
        self.assertNotContains(response, "Future question")

    ## POST /api/v1/polls/
    def test_unauthenticated_user_post_question(self):
        response = self.post_question(self.question_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_user_post_question(self):
        response = self.login_then_post_question(self.question_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_valid_question(self):
        response = self.login_then_post_question(
            create_question_data("A question", self.choices, days=-30)
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_no_choices_question(self):
        response = self.login_then_post_question(create_question_data("A question", []))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_one_choice_question(self):
        response = self.login_then_post_question(
            create_question_data("A question", create_choices_data("One choice"))
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_two_choice_question(self):
        response = self.login_then_post_question(
            create_question_data(
                "A question", create_choices_data("First choice", "Second choice")
            )
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_duplicate_question(self):
        self.login_then_post_question(
            create_question_data("A question", self.choices, days=-30)
        )

        # question with the same text as previous
        response = self.post_question(
            create_question_data("A question", self.choices, days=-30)
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_choice_question(self):
        response = self.login_then_post_question(
            create_question_data(
                "A question",
                create_choices_data(
                    "Duplicate choice", "Some choice", "Duplicate choice"
                ),
            )
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_19_choices_question(self):
        response = self.login_then_post_question(
            create_question_data(
                "A question",
                [{"choice_text": f"Choice {i}"} for i in range(19)],
                days=-30,
            )
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_20_choices_question(self):
        response = self.login_then_post_question(
            create_question_data(
                "A question",
                [{"choice_text": f"Choice {i}"} for i in range(20)],
                days=-30,
            )
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_more_than_20_choices_question(self):
        response = self.login_then_post_question(
            create_question_data(
                "A question",
                [{"choice_text": f"Choice {i}"} for i in range(21)],
                days=-30,
            )
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    ## GET /api/v1/polls/{id}/
    def test_unauthenticated_user_get_question(self):
        self.login_then_post_question(self.question_data)
        self.logout()
        response = self.get_question(question_id=1)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_user_get_question(self):
        self.login_then_post_question(self.question_data)
        response = self.get_question(question_id=1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, self.question_text)

    ## PUT /api/v1/polls/{id}/
    ## PATCH /api/v1/polls/{id}/
    def test_update_question(self):
        self.login()
        response = self.client.put(reverse("polls:question-detail", args=(1,)))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        response = self.client.patch(reverse("polls:question-detail", args=(1,)))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    ## DELETE /api/v1/polls/{id}/
    def test_unauthenticated_user_delete_question(self):
        response = self.delete_question(question_id=1)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_user_delete_question(self):
        self.login_then_post_question(
            create_question_data("First question", self.choices, days=-1)
        )
        self.post_question(
            create_question_data("Second question", self.choices, days=-1)
        )

        # Delete first question
        self.delete_question(1)

        response = self.get_questions()
        self.assertNotContains(response, "First question")
        self.assertContains(response, "Second question")

    def test_not_owner_delete_question(self):
        self.create_user_and_login("user1", "secret")
        self.post_question(self.question_data)

        self.create_user_and_login("user2", "secret")
        response = self.delete_question(1)  # user2 tries to delete user1's question

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    ## GET /api/v1/polls/{id}/choices/
    def test_unauthenticated_user_get_choices(self):
        response = self.get_choices(1)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_user_get_choices(self):
        self.login_then_post_question(
            create_question_data(
                "A question",
                create_choices_data("First choice", "Second choice"),
            )
        )
        response = self.get_choices(1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "First choice")
        self.assertContains(response, "Second choice")

    def test_not_owner_get_choices(self):
        self.create_user_and_login("user1", "secret")
        self.post_question(
            create_question_data(
                "A question",
                create_choices_data("First choice", "Second choice"),
            )
        )

        # user2 tries to view choices of question created by user1
        self.create_user_and_login("user2", "secret")
        response = self.get_choices(1)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "First choice")
        self.assertContains(response, "Second choice")

    ## POST /api/v1/polls/{id}/choices/
    def test_post_choice(self):
        self.login()
        response = self.client.post(reverse("polls:question-choice-list", args=(1,)))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    ## GET /api/v1/polls/{id}/choices/{id}/
    def test_unauthenticated_user_get_choice(self):
        response = self.get_choice(question_id=1, choice_id=1)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_user_get_choice(self):
        self.login_then_post_question(
            create_question_data(
                "A question",
                create_choices_data("First choice", "Second choice"),
            )
        )
        response = self.get_choice(question_id=1, choice_id=1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "First choice")

    def test_not_owner_get_choice(self):
        self.create_user_and_login("user1", "secret")
        self.post_question(
            create_question_data(
                "A question",
                create_choices_data("First choice", "Second choice"),
            )
        )

        # user2 tries to view first choice of question created by user1
        self.create_user_and_login("user2", "secret")
        response = self.get_choice(question_id=1, choice_id=1)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "First choice")

    def test_get_choice_of_another_question(self):
        self.login_then_post_question(
            create_question_data(
                "First question", create_choices_data("First choice", "Second choice")
            )
        )
        self.post_question(
            create_question_data(
                "Second question", create_choices_data("Third choice", "Fourth choice")
            )
        )

        # get `Third choice` from `First question`
        response = self.get_choice(question_id=1, choice_id=3)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_choice_does_not_exist(self):
        self.login_then_post_question(
            create_question_data(
                "A question", create_choices_data("First choice", "Second choice")
            )
        )

        # get `Third choice` from `First question`
        response = self.get_choice(question_id=1, choice_id=3)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_choice_vote_count(self):
        self.login_then_post_question(
            create_question_data(
                "A question", create_choices_data("First choice", "Second choice")
            )
        )
        response = self.get_choice(question_id=1, choice_id=1)
        self.assertEqual(json.loads(response.content)["vote_count"], 0)
        response = self.get_choice(question_id=1, choice_id=2)
        self.assertEqual(json.loads(response.content)["vote_count"], 0)

        # vote on question's first choice
        self.post_vote(question_id=1, choice_id=1)

        # first choice's vote count should've increased
        response = self.get_choice(question_id=1, choice_id=1)
        self.assertEqual(json.loads(response.content)["vote_count"], 1)

        # second choice's vote count should've stayed the same
        response = self.get_choice(question_id=1, choice_id=2)
        self.assertEqual(json.loads(response.content)["vote_count"], 0)

    ## PUT /api/v1/polls/{id}/choices/{id}/
    ## PATCH /api/v1/polls/{id}/choices/{id}/
    def test_update_choice(self):
        self.login()
        response = self.client.put(reverse("polls:question-choice-detail", args=(1, 1)))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        response = self.client.patch(
            reverse("polls:question-choice-detail", args=(1, 1))
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    ## DELETE /api/v1/polls/{id}/choices/{id}/
    def test_delete_choice(self):
        self.login()
        response = self.client.delete(
            reverse("polls:question-choice-detail", args=(1, 1))
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    ## GET /api/v1/polls/{id}/choices/{id}/votes/
    def test_unauthenticated_user_get_votes(self):
        response = self.get_votes(question_id=1, choice_id=1)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_user_get_votes(self):
        self.login_then_post_question(
            create_question_data(
                "A question",
                create_choices_data("First choice", "Second choice"),
            )
        )
        response = self.get_votes(question_id=1, choice_id=1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_not_owner_get_votes(self):
        self.create_user_and_login("user1", "secret")
        self.post_question(
            create_question_data(
                "A question",
                create_choices_data("First choice", "Second choice"),
            )
        )

        # user2 tries to view votes of user1's question's first choice
        self.create_user_and_login("user2", "secret")
        response = self.get_votes(question_id=1, choice_id=1)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    ## POST /api/v1/polls/{id}/choices/{id}/votes/
    def test_unauthenticated_user_post_vote(self):
        response = self.post_vote(question_id=1, choice_id=1)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_user_post_vote(self):
        self.login_then_post_question(self.question_data)
        response = self.post_vote(question_id=1, choice_id=1, data=create_vote_data())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = self.get_votes(question_id=1, choice_id=1)
        self.assertEqual(json.loads(response.content)["count"], 1)

    def test_post_vote_same_choice_2_times(self):
        self.login_then_post_question(self.question_data)
        response = self.post_vote(question_id=1, choice_id=1, data=create_vote_data())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = self.post_vote(question_id=1, choice_id=1, data=create_vote_data())
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_vote_same_question_2_times(self):
        # create question with two choices
        self.login_then_post_question(
            create_question_data(
                "A question", create_choices_data("First question", "Second question")
            )
        )

        # vote on 1st choice
        response = self.post_vote(question_id=1, choice_id=1, data=create_vote_data())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # vote on 2nd choice
        response = self.post_vote(question_id=1, choice_id=2, data=create_vote_data())
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_hiding_user_post_vote(self):
        self.login_then_post_question(self.question_data)

        # a user votes with username visible
        self.create_user_and_login(username="visibleUser", password="secret")
        self.post_vote(
            question_id=1, choice_id=1, data=create_vote_data(hide_voter=False)
        )

        # a user votes with username hidden
        self.create_user_and_login(username="hiddenUser", password="secret")
        self.post_vote(
            question_id=1, choice_id=1, data=create_vote_data(hide_voter=True)
        )

        response = self.get_votes(question_id=1, choice_id=1)
        self.assertContains(response, "visibleUser")
        self.assertNotContains(response, "hiddenUser")

    ## GET /api/v1/polls/{id}/choices/{id}/votes/{id}/
    def test_unauthenticated_user_get_vote(self):
        response = self.get_vote(question_id=1, choice_id=1, vote_id=1)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_user_get_vote(self):
        self.login_then_post_question(self.question_data)
        self.post_vote(question_id=1, choice_id=1)
        response = self.get_vote(question_id=1, choice_id=1, vote_id=1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_not_owner_get_vote(self):
        # user1 creates a question and votes on its 1st choice
        self.create_user_and_login("user1", "secret")
        self.post_question(self.question_data)
        self.post_vote(question_id=1, choice_id=1)

        # user2 tries to view user1's vote
        self.create_user_and_login("user2", "secret")
        response = self.get_vote(question_id=1, choice_id=1, vote_id=1)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_vote_does_not_exist(self):
        # create one question with two choices
        self.login_then_post_question(
            create_question_data(
                "One question", create_choices_data("First choice", "Second choice")
            )
        )

        # vote does not exist
        response = self.get_vote(question_id=1, choice_id=1, vote_id=1)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # vote's choice does not exist. question have 2 choices only
        response = self.get_vote(question_id=1, choice_id=3, vote_id=1)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # vote's question does not exist.
        response = self.get_vote(question_id=2, choice_id=1, vote_id=1)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    ## DELETE /api/v1/polls/{id}/choices/{id}/votes/{id}/
    def test_unauthenticated_user_delete_vote(self):
        response = self.delete_vote(question_id=1, choice_id=1, vote_id=1)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_user_delete_vote(self):
        # create question and vote on its 1st choice
        self.login_then_post_question(self.question_data)
        self.post_vote(question_id=1, choice_id=1)

        # 1st choice should have 1 vote
        response = self.get_votes(question_id=1, choice_id=1)
        self.assertEqual(json.loads(response.content)["count"], 1)

        # delete vote
        response = self.delete_vote(question_id=1, choice_id=1, vote_id=1)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # 1st choice should have 0 vote now
        response = self.get_votes(question_id=1, choice_id=1)
        self.assertEqual(json.loads(response.content)["count"], 0)

    def test_not_owner_delete_vote(self):
        # user1 creates a question and votes on its 1st choice
        self.create_user_and_login("user1", "secret")
        self.post_question(self.question_data)
        self.post_vote(question_id=1, choice_id=1)

        # user2 tries to delete user1's vote
        self.create_user_and_login("user2", "secret")
        response = self.delete_vote(question_id=1, choice_id=1, vote_id=1)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    ## PUT /api/v1/polls/{id}/choices/{id}/votes/{id}/
    def test_unauthenticated_user_put_vote(self):
        response = self.put_vote(question_id=1, choice_id=1, vote_id=1)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_put_vote_username_visibility(self):
        # create question and vote on its 1st choice
        self.create_user_and_login("user1", "secret")
        self.post_question(self.question_data)
        self.post_vote(question_id=1, choice_id=1)

        # voter name should be hidden by default
        response = self.get_votes(question_id=1, choice_id=1)
        self.assertNotContains(response, "user1")

        # update vote so voter name is shown
        self.put_vote(
            question_id=1,
            choice_id=1,
            vote_id=1,
            data=create_vote_data(hide_voter=False),
        )

        # voter name should be visible now
        response = self.get_votes(question_id=1, choice_id=1)
        self.assertContains(response, "user1")
        self.assertEqual(json.loads(response.content)["count"], 1)

    def test_put_vote_change_choice(self):
        # create question and vote on its 1st choice
        self.create_user_and_login("user1", "secret")
        self.post_question(self.question_data)
        self.post_vote(question_id=1, choice_id=1)

        # 1st and 2nd choice should have 1 and 0 vote respectively
        response = self.get_votes(question_id=1, choice_id=1)
        self.assertEqual(json.loads(response.content)["count"], 1)

        response = self.get_votes(question_id=1, choice_id=2)
        self.assertEqual(json.loads(response.content)["count"], 0)

        # change vote to 2nd choice
        self.put_vote(
            question_id=1,
            choice_id=1,
            vote_id=1,
            data=create_vote_data(choice=2),
        )

        # 1st and 2nd choice should have 0 and 1 vote respectively
        response = self.get_votes(question_id=1, choice_id=1)
        self.assertEqual(json.loads(response.content)["count"], 0)

        response = self.get_votes(question_id=1, choice_id=2)
        self.assertEqual(json.loads(response.content)["count"], 1)

    def test_put_vote_change_invalid_choice(self):
        # create question with two choices and vote on its 1st choice
        self.create_user_and_login("user1", "secret")
        self.post_question(
            create_question_data(
                "A question", create_choices_data("First choice", "Second choice")
            )
        )
        self.post_vote(question_id=1, choice_id=1)

        # 1st and 2nd choice should have 1 and 0 vote respectively
        response = self.get_votes(question_id=1, choice_id=1)
        self.assertEqual(json.loads(response.content)["count"], 1)

        response = self.get_votes(question_id=1, choice_id=2)
        self.assertEqual(json.loads(response.content)["count"], 0)

        # change vote to 3rd choice (does not exist)
        response = self.put_vote(
            question_id=1,
            choice_id=1,
            vote_id=1,
            data=create_vote_data(choice=3),
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # 1st and 2nd choice should have 0 and 1 vote respectively
        response = self.get_votes(question_id=1, choice_id=1)
        self.assertEqual(json.loads(response.content)["count"], 1)

        response = self.get_votes(question_id=1, choice_id=2)
        self.assertEqual(json.loads(response.content)["count"], 0)
