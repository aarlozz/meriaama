"""
IMPORTANT: Verify this wording against your own copy of the source PDFs
before using in an academic/clinical submission -- transcription errors
are easy to introduce. Cite properly wherever these are displayed:

  PSS-10: Cohen, S., Kamarck, T., & Mermelstein, R. (1983). A global
          measure of perceived stress. Journal of Health and Social
          Behavior, 24(4), 385-396.
  EPDS:   Cox, J.L., Holden, J.M., & Sagovsky, R. (1987). Detection of
          postnatal depression: Development of the 10-item Edinburgh
          Postnatal Depression Scale. British Journal of Psychiatry,
          150, 782-786.
          (Reproducible without further permission provided authors,
          title, and source are credited -- include this citation
          in the UI, not just in code.)
  GAD-7:  Spitzer, R.L., Kroenke, K., Williams, J.B., & Lowe, B. (2006).
          A brief measure for assessing generalized anxiety disorder:
          the GAD-7. Archives of Internal Medicine, 166(10), 1092-1097.
          (Public domain, freely reproducible.)

SCORING NOTE: PSS-10 items 4, 5, 7, 8 (0-indexed: 3, 4, 6, 7 below) are
reverse-scored because they are positively worded. Whatever scoring
function consumes extract_answers() output must do:
    reverse_scored_indices = {3, 4, 6, 7}
    score = sum(4 - v if i in reverse_scored_indices else v
                for i, v in enumerate(answers))
This file only fixes question text/order -- it does NOT implement that
scoring step. Make sure it's applied downstream.
"""
from django import forms
from .models import PsychometricTest

FREQUENCY_SCALE_0_4 = [(0, "Never"), (1, "Almost never"), (2, "Sometimes"), (3, "Fairly often"), (4, "Very often")]
FREQUENCY_SCALE_0_3 = [(0, "Not at all"), (1, "Several days"), (2, "More than half the days"), (3, "Nearly every day")]

QUESTIONS = {
    PsychometricTest.TestType.PSS10: {
        "scale": FREQUENCY_SCALE_0_4,
        "questions": [
            # FIXED: was "overwhelmed by unexpected events" (not an official item) --
            # replaced with the actual official PSS-10 item 1.
            "In the last month, how often have you been upset because of something that happened unexpectedly?",
            "How often have you felt unable to control important things in your life?",
            "How often have you felt nervous and stressed?",
            "How often have you felt confident about your ability to handle your personal problems?",  # reverse-scored
            "How often have you felt that things were going your way?",  # reverse-scored
            "How often have you found that you could not cope with all the things that you had to do?",
            "How often have you been able to control irritations in your life?",  # reverse-scored
            "How often have you felt that you were on top of things?",  # reverse-scored
            "How often have you been angered because of things that were outside of your control?",
            "How often have you felt difficulties were piling up so high that you could not overcome them?",
        ],
    },
    PsychometricTest.TestType.EPDS: {
        "scale": FREQUENCY_SCALE_0_3,
        "questions": [
            "I have been able to laugh and see the funny side of things.",
            "I have looked forward with enjoyment to things.",
            "I have blamed myself unnecessarily when things went wrong.",
            "I have been anxious or worried for no good reason.",
            # FIXED: was missing "very" -- original says "no very good reason".
            "I have felt scared or panicky for no very good reason.",
            "Things have been getting on top of me.",
            "I have been so unhappy that I have had difficulty sleeping.",
            "I have felt sad or miserable.",
            "I have been so unhappy that I have been crying.",
            "The thought of harming myself has occurred to me.",
        ],
    },
    PsychometricTest.TestType.GAD7: {
        "scale": FREQUENCY_SCALE_0_3,
        "questions": [
            "Feeling nervous, anxious, or on edge.",
            "Not being able to stop or control worrying.",
            "Worrying too much about different things.",
            "Trouble relaxing.",
            "Being so restless that it's hard to sit still.",
            "Becoming easily annoyed or irritable.",
            "Feeling afraid as if something awful might happen.",
        ],
    },
}


def build_test_form(test_type, data=None):
    """
    Dynamically builds a Form with one ChoiceField per question for the
    given test_type. Returns a *form instance*, not a class -- simplest to
    work with in the view since the questions differ per test type.
    """
    config = QUESTIONS[test_type]

    class DynamicPsychometricForm(forms.Form):
        pass

    for i, question_text in enumerate(config["questions"]):
        DynamicPsychometricForm.base_fields[f"q{i}"] = forms.TypedChoiceField(
            label=question_text,
            choices=config["scale"],
            coerce=int,
            widget=forms.RadioSelect,
        )

    return DynamicPsychometricForm(data)


def extract_answers(form, test_type):
    """After a valid dynamic form submit, pull ordered answers as a list of ints."""
    n_questions = len(QUESTIONS[test_type]["questions"])
    return [form.cleaned_data[f"q{i}"] for i in range(n_questions)]