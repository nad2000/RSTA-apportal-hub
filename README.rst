Prime Minister's Science Prizes
===============================

Prime Minister's Science Prizes Portal

.. image:: https://img.shields.io/badge/built%20with-Cookiecutter%20Django-ff69b4.svg
    :target: https://github.com/pydanny/cookiecutter-django/
    :alt: Built with Cookiecutter Django
.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/ambv/black
    :alt: Black code style
.. image:: https://img.shields.io/github/issues/nad2000/PMSPP
    :alt: GitHub issues
    :target: https://github.com/nad2000/PMSPP/issues
.. image:: https://img.shields.io/github/forks/nad2000/PMSPP
    :alt: GitHub forks
    :target: https://github.com/nad2000/PMSPP/network
.. image:: https://img.shields.io/github/stars/nad2000/PMSPP
    :alt: GitHub stars
    :target: https://github.com/nad2000/PMSPP/stargazers
.. image:: https://img.shields.io/travis/com/nad2000/django-cookiecutter-projects
    :alt: Travis (.com)


:License: MIT


Settings
--------

Moved to settings_.

.. _settings: http://cookiecutter-django.readthedocs.io/en/latest/settings.html

Deployment Environment
----------------------

    1. Create a Python virtual environment.

    1. Istall all dependecies.

    1. Run migrations.

    1. Create a superuser.

    1. Create a self signed server sertivificate and a key::

        $ openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365

    1. Run server with the the certificate::

        $ ./manage.py runserver_plus --cert-file cert.pem --key-file key.pem


Basic Commands
--------------

Setting Up Your Users
^^^^^^^^^^^^^^^^^^^^^

* To create a **normal user account**, just go to Sign Up and fill out the form. Once you submit it, you'll see a "Verify Your E-mail Address" page. Go to your console to see a simulated email verification message. Copy the link into your browser. Now the user's email should be verified and ready to go.

* To create an **superuser account**, use this command::

    $ python manage.py createsuperuser

For convenience, you can keep your normal user logged in on Chrome and your superuser logged in on Firefox (or similar), so that you can see how the site behaves for both kinds of users.

Type checks
^^^^^^^^^^^

Running type checks with mypy:

::

  $ mypy pmspp

Test coverage
^^^^^^^^^^^^^

To run the tests, check your test coverage, and generate an HTML coverage report::

    $ coverage run -m pytest
    $ coverage html
    $ open htmlcov/index.html

Running tests with py.test
~~~~~~~~~~~~~~~~~~~~~~~~~~

::

  $ pytest

Live reloading and Sass CSS compilation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Moved to `Live reloading and SASS compilation`_.

.. _`Live reloading and SASS compilation`: http://cookiecutter-django.readthedocs.io/en/latest/live-reloading-and-sass-compilation.html





Sentry
^^^^^^

Sentry is an error logging aggregator service. You can sign up for a free account at  https://sentry.io/signup/?code=cookiecutter  or download and host it yourself.
The system is setup with reasonable defaults, including 404 logging and integration with the WSGI application.

You must set the DSN url in production.


Deployment
----------

The following details how to deploy this application.


Heroku
^^^^^^

See detailed `cookiecutter-django Heroku documentation`_.

.. _`cookiecutter-django Heroku documentation`: http://cookiecutter-django.readthedocs.io/en/latest/deployment-on-heroku.html




