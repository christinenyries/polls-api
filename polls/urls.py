from django.urls import path, include
from rest_framework_nested import routers

from polls.views import QuestionViewSet, ChoiceViewSet, VoteViewSet


app_name = "polls"

router = routers.SimpleRouter()
router.register("", QuestionViewSet, basename="question")

question_router = routers.NestedSimpleRouter(router, "", lookup="question")
question_router.register("choices", ChoiceViewSet, basename="question-choice")

question_choice_router = routers.NestedSimpleRouter(
    question_router, "choices", lookup="choice"
)
question_choice_router.register("votes", VoteViewSet, basename="question-choice-vote")


urlpatterns = [
    path("", include(router.urls)),
    path("", include(question_router.urls)),
    path("", include(question_choice_router.urls)),
]
