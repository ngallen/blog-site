import webapp2
import os
import cgi
import jinja2
import re
import hashlib
import hmac
import random
import string
from google.appengine.ext import db

class Blog(db.Model):
	title = db.StringProperty(required=True)
	body = db.TextProperty(required = True)
	created = db.DateTimeProperty(auto_now_add=True)
	likes = db.IntegerProperty(default=0)
	author = db.TextProperty()

class User(db.Model):
	name = db.StringProperty(required = True)
	pw_hash = db.StringProperty(required = True)
	email = db.StringProperty()

	@classmethod
	def by_id(cls, uid):
		return User.get_by_id(uid, parent = db.Key.from_path('users', 'Default'))

	@classmethod
	def by_name(cls, name):
		u = User.all().filter('name =', name).get()
		return u

	@classmethod
	def register(cls, name, pw, email = None):
		pw_hash = make_pw_hash(name, pw, make_salt())
		return User(parent = db.Key.from_path('users', 'Default'),
					name = name,
					pw_hash = pw_hash,
					email = email)

	@classmethod
	def login(cls, name, pw):
		u = cls.by_name(name)
		if u and valid_pw(name, pw, u.pw_hash):
			return u

secret = 'imsosecret'

USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
def valid_username(username):
		return username and USER_RE.match(username)

PASS_RE = re.compile(r"^.{3,20}$")
def valid_password(password):
		return password and PASS_RE.match(password)

EMAIL_RE  = re.compile(r'^[\S]+@[\S]+\.[\S]+$')
def valid_email(email):
		return not email or EMAIL_RE.match(email)

def make_salt():
	return ''.join(random.sample(string.letters, 5))\

def make_pw_hash(name, pw, salt):
	hashString = hashlib.sha256(name+pw+salt).hexdigest()
	return "%s|%s" %  (salt, hashString)

def valid_pw(name, pw, h):
	salt = h.split("|")[0]
	if make_pw_hash(name, pw, salt) == h:
		return True
	else:
		return False

def make_secure_val(val):
		return '%s|%s' % (val, hmac.new(secret, val).hexdigest())

def check_secure_val(secure_val):
		val = secure_val.split('|')[0]
		if secure_val == make_secure_val(val):
				return val