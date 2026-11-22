__lazy_modules__ = ["flask", "flask_login", "functools"]

import functools

import flask
import flask_login


def is_admin(user=None) -> bool:
    if user is None:
        user = flask_login.current_user
    return not user.is_anonymous and user.is_admin


def admin_only(func):

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if flask_login.current_user.is_anonymous:
            flask.abort(401)
        if not flask_login.current_user.is_admin:
            flask.abort(403)
        return func(*args, **kwargs)

    return wrapper
