"""
IMPORTANT: The question text below is placeholder/paraphrased wording so the
form is functional out of the box. PSS-10, EPDS, and GAD-7 are published,
validated instruments -- for your actual academic submission, replace the
`QUESTIONS` text with the exact licensed wording from the original published
scales (cite them properly: Cohen et al. 1983 for PSS-10, Cox et al. 1987
for EPDS, Spitzer et al. 2006 for GAD-7), and double check any licensing
requirements for clinical/academic use of EPDS in particular.
"""
from django import forms
from .models import PsychometricTest

FREQUENCY_SCALE_0_4 = [(0, "Never"), (1, "Almost never"), (2, "Sometimes"), (3, "Fairly often"), (4, "Very often")]
FREQUENCY_SCALE_0_3 = [(0, "Not at all"), (1, "Several days"), (2, "More than half the days"), (3, "Nearly every day")]

QUESTIONS = {
    PsychometricTest.TestType.PSS10: {
        "scale": FREQUENCY_SCALE_0_4,
        "questions": [
            "How often have you felt unable to control important things in your life?",
            "How often have you felt nervous or stressed?",
            "How often have you felt confident about handling personal problems?",
            "How often have you felt things were going your way?",
            "How often have you found you could not cope with everything you had to do?",
            "How often have you been able to control irritations in your life?",
            "How often have you felt on top of things?",
            "How often have you been angered by things outside your control?",
            "How often have you felt difficulties piling up too high to overcome?",
            "How often have you felt overwhelmed by unexpected events?",
        ],
    },
    PsychometricTest.TestType.EPDS: {
        "scale": FREQUENCY_SCALE_0_3,
        "questions": [
            "I have been able to laugh and see the funny side of things.",
            "I have looked forward with enjoyment to things.",
            "I have blamed myself unnecessarily when things went wrong.",
            "I have been anxious or worried for no good reason.",
            "I have felt scared or panicky for no good reason.",
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