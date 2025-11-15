from flask import Blueprint, render_template, request, url_for, redirect,flash


bp = Blueprint("pages", __name__)

@bp.route("/guest")
def guest():
    return render_template("pages/index.html")
