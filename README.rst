The Application Portal for the Prime Ministers Science Prizes
=============================================================

A home for development of the Application Portal for the Prime Ministers Science Prizes

.. image:: https://img.shields.io/badge/built%20with-Cookiecutter%20Django-ff69b4.svg
    :target: https://github.com/pydanny/cookiecutter-django/
    :alt: Built with Cookiecutter Django
.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/ambv/black
    :alt: Black code style
.. image:: https://img.shields.io/github/issues/Royal-Society-of-New-Zealand/RSTA-apportal-hub
    :alt: GitHub issues
    :target: https://github.com/Royal-Society-of-New-Zealand/RSTA-apportal-hub
.. image:: https://img.shields.io/github/forks/Royal-Society-of-New-Zealand/RSTA-apportal-hub
    :alt: GitHub forks
    :target: https://github.com/Royal-Society-of-New-Zealand/RSTA-apportal-hub
.. image:: https://img.shields.io/github/stars/Royal-Society-of-New-Zealand/RSTA-apportal-hub
    :alt: GitHub stars
    :target: https://github.com/Royal-Society-of-New-Zealand/RSTA-apportal-hub
.. image:: https://img.shields.io/travis/com/nad2000/django-cookiecutter-projects
    :alt: Travis (.com)


Settings
--------

Moved to settings_.

.. _settings: http://cookiecutter-django.readthedocs.io/en/latest/settings.html

Deployment Environment
----------------------

1. Create a Python virtual environment.

#. Istall all dependecies.

#. Run migrations.

#. Create a superuser.

#. Run server with the the certificate::

    $ ./manage.py runserver_plus --cert-file cert.crt --key-file cert.key

#. To make life easier, add import the crt file as a trusted server sertificate in your browser (read more at: https://support.google.com/chrome/a/answer/6342302).


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

  $ mypy portal

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

