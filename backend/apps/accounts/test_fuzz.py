from hypothesis import given, settings
from hypothesis import strategies as st
from hypothesis.extra.django import TestCase as HypothesisTestCase

from apps.accounts.models import User
from apps.accounts.serializers import RegisterSerializer


safe_text = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters=["\x00"]),
    max_size=80,
)
password_tail = st.text(alphabet=list("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*"), min_size=5, max_size=29)
valid_passwords = st.builds(
    lambda upper, lower, digit, tail: f"{upper}{lower}{digit}{tail}",
    st.sampled_from(list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")),
    st.sampled_from(list("abcdefghijklmnopqrstuvwxyz")),
    st.sampled_from(list("0123456789")),
    password_tail,
)


class RegisterSerializerFuzzTests(HypothesisTestCase):
    @settings(max_examples=120, deadline=None)
    @given(
        email=st.one_of(st.emails(), safe_text),
        username=safe_text,
        first_name=safe_text,
        last_name=safe_text,
        role=st.text(max_size=20),
        password=safe_text,
    )
    def test_register_serializer_handles_random_input_without_crashing(
        self,
        email,
        username,
        first_name,
        last_name,
        role,
        password,
    ):
        serializer = RegisterSerializer(
            data={
                "email": email,
                "username": username,
                "first_name": first_name,
                "last_name": last_name,
                "role": role,
                "password": password,
            }
        )

        self.assertIsInstance(serializer.is_valid(), bool)

    @settings(max_examples=60, deadline=None)
    @given(
        email=st.emails(),
        username=st.from_regex(r"[A-Za-z][A-Za-z0-9_]{2,24}", fullmatch=True),
        role=st.sampled_from([User.Roles.STUDENT, User.Roles.TEACHER]),
        password=valid_passwords,
    )
    def test_valid_student_or_teacher_registration_data_is_accepted(
        self,
        email,
        username,
        role,
        password,
    ):
        serializer = RegisterSerializer(
            data={
                "email": email,
                "username": username,
                "role": role,
                "password": password,
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)

    @settings(max_examples=60, deadline=None)
    @given(
        email=st.emails(),
        username=st.from_regex(r"[A-Za-z][A-Za-z0-9_]{2,24}", fullmatch=True),
        password=valid_passwords,
    )
    def test_admin_registration_data_is_rejected(self, email, username, password):
        serializer = RegisterSerializer(
            data={
                "email": email,
                "username": username,
                "role": User.Roles.ADMIN,
                "password": password,
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("role", serializer.errors)
