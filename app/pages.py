from flask import Blueprint, render_template, request, url_for, redirect,flash, send_file,abort, session,Flask
from .models import user, SSID
from app.routes import register_blueprints
from app import db
import logging 

app=Flask(__name__)
log = logging.getLogger(__name__)
bp = Blueprint("pages", __name__)


register_blueprints(app)


@bp.route("/")
def guest():
    users = user.query.all()
    if len(users) == 0:
        return redirect(url_for("pages.initApp"))
    ssids=db.session.query(SSID)
    guestSSID = ssids.filter_by(isGuest=True).first()
    return render_template("pages/index.html",guest=guestSSID)








