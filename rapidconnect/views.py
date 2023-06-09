from hashlib import md5
from urllib.parse import urljoin

import jwt
import requests
from allauth.account.utils import get_next_redirect_url
from allauth.socialaccount import providers
from allauth.socialaccount.helpers import (
    complete_social_login,
    render_authentication_error,
)
from allauth.socialaccount.models import SocialLogin, SocialToken
from allauth.socialaccount.providers.base import AuthError
from allauth.utils import get_request_param
from django.contrib.auth import get_user_model
from django.core import signing
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.utils.http import urlencode
from django.views.decorators.csrf import csrf_exempt

from .provider import ATTRIBUTE_KEY, BASE_URL, RapidConnectProvider


class RapidConnectApiError(Exception):
    pass


def login(request):
    app = providers.registry.by_id(RapidConnectProvider.id, request).get_app(request)

    url = app.client_id
    if BASE_URL:
        url = urljoin(BASE_URL, url)
        request.build_absolute_uri()

    state = {}
    next_url = get_next_redirect_url(request)
    if next_url:
        state["next"] = next_url
    process = get_request_param(request, "process", "login")
    state["process"] = process
    if process == "connect" and request.user.is_authenticated:
        state["user_id"] = request.user.id

    verifier = get_random_string(length=36)

    cookie_name = RapidConnectProvider.id + ":state"
    cookie_value = signing.dumps(
        (
            state,
            verifier,
        )
    )

    response = HttpResponseRedirect(url)
    response.set_cookie(cookie_name, cookie_value)

    return response


@csrf_exempt
def callback(request):

    ret = None
    auth_exception = None

    try:
        app = providers.registry.by_id(RapidConnectProvider.id, request).get_app(request)
        audience = request.scheme + "://" + request.get_host()
        token = jwt.decode(
            request.POST["assertion"],
            app.secret,
            audience=audience,
            verify=False,
            algorithms=["HS256"],
        )
        attributes = token[ATTRIBUTE_KEY]

        provider = providers.registry.by_id(RapidConnectProvider.id, request)
        login = provider.sociallogin_from_response(request, attributes)
        login.token = SocialToken(app=app, token=token["jti"])

        cookie_name = RapidConnectProvider.id + ":state"
        if cookie_name not in request.COOKIES:
            raise PermissionDenied()

        state, verifier = signing.loads(request.COOKIES[cookie_name])
        process, user_id = state.get("process"), state.get("user_id")
        if process == "connect" and user_id and not request.user.is_authenticated:
            request.user = get_user_model().objects.get(pk=int(user_id))

        login.state = state

        ret = complete_social_login(request, login)
    except (requests.RequestException, RapidConnectApiError) as e:
        auth_exception = e

    if not ret:
        ret = render_authentication_error(
            request, RapidConnectProvider.id, exception=auth_exception
        )

    ret.delete_cookie(cookie_name)
    return ret


def logout(request):
    app = providers.registry.by_id(RapidConnectProvider.id, request).get_app(request)
    url = app.client_id or BASE_URL
    url = urljoin(url, "/logout")

    return_url = get_next_redirect_url(request) or request.build_absolute_uri(reverse("home"))
    url += "?return=" + return_url
    response = HttpResponseRedirect(url)

    return response
