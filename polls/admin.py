from django.contrib import admin

from .models import Question, Choice, Vote


class VoteInline(admin.TabularInline):
    model = Vote
    extra = 3


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 3


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("question_text", "date_published", "date_created")
    list_filter = ("date_published", "date_created")
    search_fields = ("question_text",)
    ordering = ("-date_published",)
    inlines = (ChoiceInline,)


@admin.register(Choice)
class ChoiceAdmin(admin.ModelAdmin):
    list_display = ("choice_text", "question")
    inlines = (VoteInline,)
