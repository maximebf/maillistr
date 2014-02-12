from flask import Flask, request, jsonify, abort
from flask.ext.sqlalchemy import SQLAlchemy
from wtforms import Form, StringField, validators
from sqlalchemy import func
from sqlalchemy.orm import backref
from functools import wraps
from flask_script import Manager, Server
import json


import gevent
from gevent import monkey; monkey.patch_all()


app = Flask(__name__)
app.config.from_pyfile('settings.py')

db = SQLAlchemy(app)
manager = Manager(app)


# ---------------------------------------------------------------
# MODELS
# ---------------------------------------------------------------


class EmailList(db.Model):
    __tablename__ = 'lists'
    slug = db.Column(db.String, primary_key=True)
    mailchimp_list_id = db.Column(db.String)
    added_at = db.Column(db.DateTime, default=func.now())

    def to_dict(self):
        return {"slug": self.slug,
                "mailchimp_list_id": self.mailchimp_list_id,
                "added_at": self.added_at.isoformat(),
                "nb_entries": self.entries.count()}


class EmailListEntry(db.Model):
    __tablename__ = 'list_entries'
    id = db.Column(db.Integer, primary_key=True)
    list_slug = db.Column(db.String, db.ForeignKey('lists.slug'))
    email_list = db.relationship('EmailList', backref=backref('entries', lazy='dynamic'), cascade='all')
    email = db.Column(db.String)
    ip = db.Column(db.String)
    added_at = db.Column(db.DateTime, default=func.now())

    def to_dict(self):
        return {"email": self.email,
                "ip": self.ip,
                "added_at": self.added_at.isoformat()}


# ---------------------------------------------------------------
# FORMS
# ---------------------------------------------------------------


class EmailForm(Form):
    email = StringField("Email", validators=[validators.DataRequired(), validators.Email()])


# ---------------------------------------------------------------
# MAILCHIMP
# ---------------------------------------------------------------


mailchimp_api = None
if app.config['MAILCHIMP']:
    import mailchimp
    mailchimp_api = mailchimp.Mailchimp(app.config['MAILCHIMP_APIKEY'])


def add_to_mailchimp_list(list_id, email):
    try:
        app.logger.debug('Adding %s to mailchimp list %s' % (email, list_id))
        mailchimp_api.lists.subscribe(list_id, {'email': email},
            double_optin=False, update_existing=True, send_welcome=False)
        app.logger.debug('Added %s to mailchimp list %s' % (email, list_id))
    except Exception as e:
        app.logger.error("Failed adding %s to mailchimp list %s" % (email, list_id))
        app.logger.error(e)


# ---------------------------------------------------------------
# COMMANDS
# ---------------------------------------------------------------


manager.add_command("run", Server())


@manager.command
def init():
    createdb()
    api_key = genapikey()
    with open('settings.py', 'a') as f:
        f.write("\nAPI_KEY = '%s'" % api_key)
    print "You API key is %s" % api_key


@manager.command
def createdb():
    db.create_all()


@manager.command
def genapikey():
    import os, binascii
    return binascii.b2a_hex(os.urandom(15))


@manager.command
def createlist(slug, mailchimp_list_id=None):
    if EmailList.query.filter_by(slug=slug).count() > 0:
        raise Exception("List already exists")
    elist = EmailList(slug=slug, mailchimp_list_id=mailchimp_list_id)
    db.session.add(elist)
    db.session.commit()


@manager.command
def dellist(slug):
    elist = EmailList.query.filter_by(slug=slug).first()
    db.session.delete(elist)
    db.session.commit()


@manager.command
def lists():
    for l in EmailList.query.all():
        print l.slug


# ---------------------------------------------------------------
# DECORATORS
# ---------------------------------------------------------------


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or auth.username != app.config['API_KEY']:
            abort(403)
        return f(*args, **kwargs)
    return decorated


def require_list(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        kwargs['elist'] = EmailList.query.filter_by(slug=kwargs.pop('slug')).first_or_404()
        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------------
# VIEWS
# ---------------------------------------------------------------


@app.route('/')
@require_auth
def list_lists():
    lists = [l.to_dict() for l in EmailList.query.all()]
    return jsonify(success=True, lists=lists)


@app.route('/<slug>', methods=['POST'])
@require_auth
def add_list(slug):
    try:
        createlist(slug, request.values.get('mailchimp_list_id'))
        return jsonify(success=True)
    except:
        return jsonify(success=False, error="List already exists")


@app.route('/<slug>')
@require_auth
@require_list
def show_list(elist):
    return jsonify(success=True, list=elist.to_dict())


@app.route('/<slug>', methods=['DELETE'])
@require_auth
@require_list
def delete_list(elist):
    db.session.delete(elist)
    db.session.commit()
    return jsonify(success=True)


@app.route('/<slug>/entries', methods=['POST'])
@app.route('/<slug>/entries/jsonp')
@require_list
def add_entry(elist):
    form = EmailForm(request.values)

    def format_resp(**kwargs):
        if request.url_rule.rule == '/<slug>/entries/jsonp':
            return "%s(%s);" % (request.args['callback'], json.dumps(kwargs))
        return jsonify(**kwargs)

    if not form.validate():
        return format_resp(success=False, error=", ".join(form.email.errors))

    if elist.entries.filter_by(email=form.email.data).count() > 0:
        return format_resp(success=True, already_added=True)

    entry = EmailListEntry(email=form.email.data, ip=request.remote_addr)
    elist.entries.append(entry)
    db.session.add(entry)
    db.session.commit()

    if app.config['MAILCHIMP'] and elist.mailchimp_list_id is not None:
        gevent.spawn(add_to_mailchimp_list, elist.mailchimp_list_id, form.email.data)

    return format_resp(success=True, already_added=False)


@app.route('/<slug>/entries', methods=['GET'])
@require_auth
@require_list
def list_entries(elist):
    entries = [e.to_dict() for e in elist.entries]
    return jsonify(success=True, nb_entries=len(entries), entries=entries)


@app.route('/<slug>/entries.csv', methods=['GET'])
@require_auth
@require_list
def list_entries_csv(elist):
    entries = [e.email for e in elist.entries]
    return "\n".join(entries)


# ---------------------------------------------------------------


if __name__ == '__main__':
    manager.run()