from django.urls import reverse
from django.conf import settings
from django.db import models, transaction
from django.db.models.functions import Coalesce
from django.db.models import Q
from django.utils import timezone

# Managers
class QuestionManager(models.Manager):
    @transaction.atomic
    def create(self, author, question_text, date_published, choices):
        question = Question(
            author=author, question_text=question_text, date_published=date_published
        )
        question.save()
        for choice in choices:
            choice = Choice(question=question, choice_text=choice.get("choice_text"))
            choice.save()

        return question


class PublishedQuestionManager(QuestionManager):
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .annotate(choice_count=Coalesce(models.Count("choice"), 0))
            .exclude(Q(date_published__gt=timezone.now()) | Q(choice_count=0))
            .order_by("-date_published")
        )


class ChoiceManager(models.Manager):
    def with_vote_count(self):
        return self.annotate(vote_count=Coalesce(models.Count("vote"), 0))


# Models
class Question(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    question_text = models.CharField(max_length=200, unique=True)
    date_published = models.DateTimeField()
    date_created = models.DateTimeField(auto_now_add=True)

    objects = QuestionManager()
    published_objects = PublishedQuestionManager()

    def get_absolute_url(self):
        return reverse("polls:question-detail", args=(self.pk,))

    def __str__(self):
        return self.question_text


class Choice(models.Model):
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="choices",
        related_query_name="choice",
    )
    choice_text = models.CharField(max_length=200)

    objects = ChoiceManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["question", "choice_text"], name="unique_choices_per_question"
            ),
        ]

    def get_absolute_url(self):
        return reverse("polls:question-choice-detail", args=(self.question.pk, self.pk))

    def __str__(self):
        return self.choice_text


class Vote(models.Model):
    voter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    choice = models.ForeignKey(
        Choice,
        on_delete=models.CASCADE,
        related_name="votes",
        related_query_name="vote",
    )
    hide_voter = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["voter", "choice"], name="unique_voters_per_choice"
            ),
        ]

    def __str__(self):
        return f"'{self.voter}' voted '{self.choice}'"
