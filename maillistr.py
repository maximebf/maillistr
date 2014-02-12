from flask import Flask, request, jsonify, abort
from flask.ext.sqlalchemy import SQLAlchemy
from flask_wtf import Form
from wtforms import StringField
from wtforms.fields.html5 import EmailField
from wtforms.validators import Required
from sqlalchemy import func
from sqlalchemy.orm import backref
from functools import wraps
from flask_script import Manager, Server


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
    added_to_mailchimp = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {"email": self.email,
                "ip": self.ip,
                "added_at": self.added_at.isoformat(),
                "added_to_mailchimp": self.added_to_mailchimp}


# ---------------------------------------------------------------
# FORMS
# ---------------------------------------------------------------


class EmailForm(Form):
    email = EmailField("Email", validators=[Required()])


# ---------------------------------------------------------------
# MAILCHIMP
# ---------------------------------------------------------------


mailchimp_api = None
if app.config['MAILCHIMP']:
    import mailchimp
    mailchimp_api = mailchimp.Mailchimp(app.config['MAILCHIMP_APIKEY'])


def add_to_mailchimp_list(list_id, email):
    try:
        mailchimp_api.lists.subscribe(list_id, {'email': email},
            double_optin=False, update_existing=True, send_welcome=False)
        return True
    except Exception as e:
        app.logger.error("Failed adding '%s' to mailchimp list" % email)
        app.logger.error(e)
        return False


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
@require_list
def add_entry(elist):
    form = EmailForm()
    if not form.validate_on_submit():
        return jsonify(success=False, errors=form.errors)

    entry = EmailListEntry(email=form.email.data, ip=request.remote_addr)
    elist.entries.append(entry)

    if app.config['MAILCHIMP']:
        entry.added_to_mailchimp = add_to_mailchimp_list(elist.mailchimp_list_id, form.email.data)

    db.session.add(entry)
    db.session.commit()
    return jsonify(success=True)

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