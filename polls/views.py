from rest_framework import viewsets, mixins

from .models import Question, Choice, Vote
from .serializers import ChoiceSerializer, QuestionSerializer, VoteSerializer
from .permissions import IsAuthorOrReadOnly, IsVoterOnly


class QuestionViewSet(
    viewsets.GenericViewSet,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
):
    queryset = Question.published_objects.all()
    serializer_class = QuestionSerializer
    permission_classes = (IsAuthorOrReadOnly,)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class ChoiceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ChoiceSerializer

    def get_queryset(self):
        return Choice.objects.with_vote_count().filter(
            question=self.kwargs["question_pk"]
        )


class VoteViewSet(viewsets.ModelViewSet):
    serializer_class = VoteSerializer
    permission_classes = (IsVoterOnly,)

    def get_serializer_context(self):
        return {
            **super().get_serializer_context(),
            "question_pk": self.kwargs["question_pk"],
            "choice_pk": self.kwargs["choice_pk"],
        }

    def perform_create(self, serializer):
        kwargs = dict(voter=self.request.user)
        if serializer.validated_data.get("choice") == None:
            kwargs["choice"] = Choice.objects.get(pk=self.kwargs["choice_pk"])
        serializer.save(**kwargs)

    def get_queryset(self):
        return Vote.objects.filter(choice=self.kwargs["choice_pk"])
