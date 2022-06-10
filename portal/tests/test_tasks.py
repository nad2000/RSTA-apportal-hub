# import pytest
# from background_task.tasks import tasks
# from django.contrib.auth import get_user_model

# from portal.tasks import notify_user

# User = get_user_model()


# @pytest.mark.django_db
# def test_submit_task():
#     username, password = "tester", "p455w0rd"
#     user = User.objects.create_user(username=username, password=password)
#     notify_user(user.id, "TEST MESSAGE")
#     assert tasks.run_next_task()
