import webapp2
import os
import cgi
import jinja2
import re
import hashlib
import hmac
import random
import string
import primary
import time

#All primary sub-functions used within this page are located
#primary.py

template_dir = os.path.join(os.path.dirname(__file__), 'html')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
	autoescape = True)

def makeActive(num):
		activeNav = ['','','','','','','','','','','']
		for i in range(0, 9):
			if i == num:
				activeNav[i] = ['active']
			else:
				activeNav[i] = ['inactive']
		return activeNav

"""Purpose: Base set of functions used throughout the project
Functions: Sets the user ID cookie.
Checks the user ID cookie for a valid value.
Renders html pages.
Provides login/logout functions.
"""
class BaseHandler(webapp2.RequestHandler):
	def __init__(self, *a, **kw):
		webapp2.RequestHandler.initialize(self, *a, **kw)
		uid = self.read_secure_cookie('user_id')
		if uid:
			self.user = primary.User.by_id(int(uid))
		else:
			self.user = None

	def set_secure_cookie(self, name, val):
		cookie_val = primary.make_secure_val(val)
		self.response.headers.add_header('Set-Cookie','%s=%s; Path=/' % (name, cookie_val))

	def read_secure_cookie(self, name):
		cookie_val = self.request.cookies.get(name)
		return cookie_val and primary.check_secure_val(cookie_val)

	def write(self, *a, **kw):
		self.response.out.write(*a, **kw)

	def renderPage(self, template, **params):
		if self.user:
			params['user'] = self.user
		t = jinja_env.get_template(template)
		self.write(t.render(params))

	def login(self, user):
		self.set_secure_cookie('user_id', str(user.key().id()))

	def logout(self):
		self.response.headers.add_header('Set-Cookie', 'user_id=; Path=/')

"""Purpose: Shows a list of all blog posts
Functions: Allows manipulation of the like/dislike score.
No limit is set for like/dislike (none required in project rubric)
Clicking on blog post subject line takes the user to the 'edit/delete'
page only if the user ID matches the post author.
"""
class MainPage(BaseHandler):
	def get(self):
		posts = primary.db.GqlQuery("SELECT * FROM Blog ORDER BY created DESC")
		error = self.request.get("error")
		self.renderPage("index.html",
			posts=posts,
			error=error,
			activeNav = makeActive(0))

	def post(self):
		error = ""
		blogID = self.request.get('blogID')
		post = primary.Blog.get_by_id(int(blogID))
		if self.user and self.user.name != post.author:
			if int(self.request.get('like')) > 0:
				post.likes = post.likes +1
			else:
				post.likes = post.likes -1
			post.put()
			time.sleep(0.2)
		else:
			error = "you can't like your own post, that would be biased"
		posts = primary.db.GqlQuery("SELECT * FROM Blog ORDER BY created DESC")
		self.renderPage("index.html",
										posts=posts,
										error=error,
										activeNav = makeActive(0))

"""Purpose: Redirects default loading page to /blog
"""
class RedirPage(BaseHandler):
	def get(self):
		self.redirect('/blog')

"""Purpose: Signup page is used to create a new user id.
Functions: Basic syntax checking is done on form data.
Username is checked for duplicates.
Cookie is created to identify user.
"""
class Signup(BaseHandler):
	def get(self):
		self.renderPage("signup-form.html",
										username="",
										password="",
										verify="",
										email="",
										activeNav = makeActive(3))

	def post(self):
		have_error = False
		username = self.request.get('username')
		password = self.request.get('password')
		verify = self.request.get('verify')
		email = self.request.get('email')
		params = dict(username = username, password=password, verify=verify, email = email, activeNav = makeActive(4))

		if not primary.valid_username(username):
			params['error_username'] = "That's not a valid username."
			have_error = True

		if not primary.valid_password(password):
			params['error_password'] = "That wasn't a valid password."
			have_error = True
		elif password != verify:
			params['error_verify'] = "Your passwords didn't match."
			params['verify'] = ''
			have_error = True

		if not primary.valid_email(email):
			params['error_email'] = "That's not a valid email."
			have_error = True

		if have_error:
			self.renderPage('signup-form.html', **params)
		else:
			u = primary.User.by_name(username)
			if u:
				params['error_username'] = "That username is already taken"
				self.renderPage('signup-form.html', **params)
			else:
				u = primary.User.register(username, password, email)
				u.put()
				self.login(u)
				self.redirect('/blog/welcome')

"""Purpose: Welcome page is activated after a user logs in.
Functions: A valid cookie check is made to validate the user.
If this check fails the user is sent to the signup page.
"""
class Welcome(BaseHandler):
	def get(self):
		if self.user:
			self.renderPage('welcome.html',
											username = self.user.name,
											activeNav = makeActive(-1))
		else:
			self.logout()
			self.redirect('/blog/signup')

"""Purpose: Creates a new blog post
Functions: Basic error checking.
Stores blog post info in database.
"""
class NewPost(BaseHandler):
	def render_newpost(self, title="", body="", error=""):
		self.renderPage("newpost.html",
										title=title,
										body=body,
										error=error,
										activeNav = makeActive(1))

	def get(self):
		if self.user:
			self.render_newpost()
		else:
			self.redirect("/blog/login")

	def post(self):
		title = self.request.get("blog-title")
		body = self.request.get("blog-body")

		if title and body:
			newBlogPost = primary.Blog(title=title, body=body, likes=0, author = self.user.name)
			newBlogPost.put()

			self.redirect("/blog/"+str(newBlogPost.key().id()))
		else:
			error = "we need both a title and a body!"
			self.render_newpost(title, body, error)

"""Purpose: Blog post perma page is used to edit/delete a post.
Functions: Access is only allowed if the blog author field matches
the user cookie identification.
"""
class PermaPage(BaseHandler):
	def get(self, blog_id):
		post = primary.Blog.get_by_id(int(blog_id))
		if self.user and self.user.name == post.author:
			self.renderPage("permalink.html",
											post=post,
											activeNav = makeActive(4))
		else:
			self.redirect("/blog?error=Invalid user identity")

	def post(self, blog_id):
		title = self.request.get("blog-title")
		body = self.request.get("blog-body")
		post = primary.Blog.get_by_id(int(blog_id))
		error = "we need both a title and a body!"
		action = self.request.get("action")
		if action == "update":
			if title and body:
				post.title = title
				post.body = body
				post.put()
				time.sleep(0.2)
				self.redirect("/blog")
			else:
				self.renderPage("permalink.html",
											post=post,
											error = error,
											activeNav = makeActive(4))
		else:
			post.delete()
			time.sleep(0.2)
			self.redirect("/blog")

"""Purpose: Login class for returning user.
Functions: Basic incorrect username/password handling.
Cookie is activated if login info matches user info stored
in database
"""
class Login(BaseHandler):
	def get(self):
		self.renderPage('login-form.html', activeNav = makeActive(2))

	def post(self):
		username = self.request.get('username')
		password = self.request.get('password')

		u = primary.User.login(username, password)
		if u:
			self.login(u)
			self.redirect('/blog')
		else:
			msg = 'Invalid login'
			self.renderPage('login-form.html',
											error = msg,
											activeNav = makeActive(2))

"""Purpose: Logs the user out.
Functions: Sets the user ID cookie to None.
"""
class Logout(BaseHandler):
	def get(self):
		self.logout()
		self.redirect('/blog/signup')

app = webapp2.WSGIApplication([('/', RedirPage),
															 ('/blog', MainPage),
															 ('/blog/signup', Signup),
															 ('/blog/welcome', Welcome),
															 ('/blog/login', Login),
															 ('/blog/logout', Logout),
															 ('/blog/newpost', NewPost),
															 (r'/blog/(\d+)', PermaPage)],
															debug=True)