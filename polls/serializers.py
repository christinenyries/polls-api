from rest_framework import serializers

from .models import Question, Choice, Vote


class DynamicFieldsModelSerializer(serializers.ModelSerializer):
    """
    A ModelSerializer that takes an additional `fields` argument that
    controls which fields should be displayed.
    """

    def __init__(self, *args, **kwargs):
        # Don't pass the 'fields' arg up to the superclass
        fields = kwargs.pop("fields", None)

        # Instantiate the superclass normally
        super().__init__(*args, **kwargs)

        if fields is not None:
            # Drop any fields that are not specified in the `fields` argument.
            allowed = set(fields)
            existing = set(self.fields)
            for field_name in existing - allowed:
                self.fields.pop(field_name)


class VoteSerializer(DynamicFieldsModelSerializer):
    voter_username = serializers.SerializerMethodField()

    class Meta:
        model = Vote
        fields = (
            "id",
            "voter_username",
            "choice",
            "hide_voter",
        )
        extra_kwargs = {
            "hide_voter": {"write_only": True},
            "choice": {"write_only": True, "required": False},
        }

    def get_voter_username(self, obj) -> str:
        return "*******" if obj.hide_voter else obj.voter.username

    def validate_choice(self, choice):
        question_pk = self.context.get("question_pk")
        question = Question.published_objects.get(pk=question_pk)
        valid_choices = question.choices

        if not valid_choices.contains(choice):
            raise serializers.ValidationError("Is not accepted by this question.")

        return choice

    def validate(self, attrs):
        question_pk = self.context.get("question_pk")
        question = Question.published_objects.get(pk=question_pk)
        valid_choices = question.choices

        request = self.context.get("request")
        voter_pk = request.user.pk
        if request.method == "POST" and valid_choices.filter(vote__voter=voter_pk):
            raise serializers.ValidationError("Multiple voting detected.")

        return attrs


class ChoiceSerializer(serializers.ModelSerializer):
    url = serializers.CharField(source="get_absolute_url", read_only=True)
    vote_count = serializers.SerializerMethodField()

    class Meta:
        fields = ("id", "url", "choice_text", "vote_count")
        model = Choice

    def get_vote_count(self, obj) -> int:
        return obj.vote_count


class QuestionSerializer(serializers.ModelSerializer):
    url = serializers.CharField(source="get_absolute_url", read_only=True)
    choices = ChoiceSerializer(many=True, write_only=True)

    class Meta:
        fields = (
            "id",
            "url",
            "author",
            "question_text",
            "date_published",
            "date_created",
            "choices",
        )
        model = Question
        extra_kwargs = {"author": {"read_only": True}}

    def validate_choices(self, choices):
        if len(choices) < 2:
            raise serializers.ValidationError("Should be at least two.")

        if len(choices) > 20:
            raise serializers.ValidationError("Should not be more than 20.")

        choice_texts = [choice.get("choice_text") for choice in choices]
        if len(set(choice_texts)) != len(choice_texts):
            raise serializers.ValidationError("Should be unique.")
        return choices

    def create(self, validated_data):
        question = Question.objects.create(
            author=validated_data.get("author"),
            question_text=validated_data.get("question_text"),
            date_published=validated_data.get("date_published"),
            choices=validated_data.get("choices"),
        )
        return question
