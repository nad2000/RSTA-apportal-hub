from typing import Any, Sequence

import faker
from django.contrib.auth import get_user_model
from factory import DjangoModelFactory, Faker, post_generation

_faker = faker.Faker()


class UserFactory(DjangoModelFactory):

    username = Faker("user_name")
    email = Faker("email")
    name = Faker("name")
    first_name = Faker("first_name")
    last_name = Faker("last_name")

    @post_generation
    def password(self, create: bool, extracted: Sequence[Any], **kwargs):

        password = extracted or _faker.password(
            length=42, special_chars=True, digits=True, upper_case=True, lower_case=True
        )
        self.set_password(password)

    class Meta:
        model = get_user_model()
        django_get_or_create = ["username"]
