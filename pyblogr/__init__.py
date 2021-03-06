# -*- coding: utf-8 -*-
import os
import sqlite3
import json
import hashlib
from datetime import datetime

from flask import Flask, render_template, flash, request, redirect, url_for, make_response, session, abort, g
from markdown import markdown



def connect_db():
  db = sqlite3.connect(app.config['database'])
  db.row_factory = sqlite3.Row
  return db

def formatDate(isodate):
  
  monthsFR = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet',
              'août', 'septembre', 'octobre', 'novembre', 'décembre']
  
  timehandler = datetime.strptime(isodate, app.config['date_format'])
  month = timehandler.month - 1
  return unicode(timehandler.strftime("%d "+monthsFR[month]+" %Y à %Hh%M"), 'utf-8')

def require_login():
  if not session.has_key('username'):
    abort(401)
  return 0

app = Flask(__name__)

@app.before_request
def before_request():
  g.db = connect_db()
    
@app.teardown_request
def teardown_request(exception):
  if hasattr(g, 'db'):
    g.db.close()

@app.route('/')
def index():
  cur = g.db.cursor()
  cur.execute('SELECT rowid, title, content, datetime FROM entries ORDER BY rowid DESC')
  data = cur.fetchall() 
  posts = []
  for row in data:
    posts.append({'rowid': row['rowid'],
                  'title': row['title'],
                  'content': row['content'],
                  'datetime': formatDate(row['datetime'])})
  return render_template('list_posts.html', posts=posts, session=session)

@app.route('/post/<int:postId>')
def show_news(postId):
  cur = g.db.cursor()
  cur.execute('SELECT * FROM entries WHERE rowid=?', (postId,))
  data = cur.fetchone()
  post = {'title': data['title'],
          'content': data['content'],
          'datetime': formatDate(data['datetime'])}
  
  return render_template('one_post.html', post=post)

@app.route('/manage/add', methods=['POST', 'GET'])
def add_post():
  require_login()
  if request.method == 'POST':
      title = request.form['title']
      content = markdown(request.form['content'])
      timestamp = datetime.now().strftime(app.config['date_format'])
      if content:
        cur = g.db.cursor()
        cur.execute('INSERT INTO entries(type, title, content, datetime) VALUES (?, ?, ?, ?)',("text", title, content, timestamp))
        g.db.commit()
        flash('Post added successfully.')
        return redirect(url_for('manage'))
      else:
        flash('You have to write something in your post !', 'error')
  return render_template('add_post.html')

@app.route('/manage/delete')
def list_posts_deletion():
  require_login()
  cur = g.db.cursor()
  cur.execute('SELECT rowid, title FROM entries')
  posts = cur.fetchall()
  return render_template('del_post.html', posts=posts)

@app.route('/manage/del/<int:postId>')
def delete_post(postId):
  require_login()
  cur = g.db.cursor()
  cur.execute('DELETE FROM entries WHERE rowid=?', (postId,))
  g.db.commit()
  flash('Post successfully deleted.')
  return redirect(url_for('list_posts_deletion'))

@app.route('/rss')
def rss():
  flash('No rss (yet).', 'error')
  return redirect(url_for('index'))

@app.route('/search')
def search():
  resp = make_response()
  resp.status = '302 Found'
  if request.args:
    resp.headers['Location'] = '/search/'+request.args.get('q', '')
    return resp
  else:
    return redirect(url_for('index'))
  
@app.route('/search/<keyword>')
def search_handler(keyword):
  cur = g.db.cursor()
  cur.execute('SELECT * FROM entries WHERE entries MATCH ?', (keyword,))
  posts = cur.fetchall()
  return render_template('search.html', keyword=keyword, posts=posts)

@app.route('/login', methods=['GET', 'POST'])
def login():
  if session.has_key('username'):
    flash('You\'re already logged in !')
    return redirect(url_for('index'))

  if app.config['DEBUG']:
    session['username'] = "DEBUG"
    flash('Logged in as debug user !')
    return redirect(url_for('manage'))

  if request.method == "POST":
    cur = g.db.cursor()
    cur.execute("SELECT * FROM users WHERE username=?", (request.form['username'],))
    login_info = cur.fetchone()
    if login_info == None:
      flash('Wrong credentials, please try again.', 'error')
      return render_template('login.html')

    auth_string = hashlib.sha256(login_info['salt']+request.form['password']).hexdigest()
    
    if auth_string == login_info['password']:
      session['username'] = request.form['username']
      flash('Successfully logged in !')
      return redirect(url_for('manage'))
    else:
      flash('Wrong credentials, please try again.', 'error')

  return render_template('login.html')

@app.route('/logout')
def logout():
  require_login()
  session.pop('username', None)
  flash("Successfully logged out.")
  return redirect(url_for('index'))

@app.route('/manage')
def manage():
  require_login()
  return render_template('manage.html', session=session)

@app.errorhandler(404)
def page_not_found(error):
    return render_template('page_not_found.html'), 404

@app.errorhandler(401)
def unauthorized(error):
    return render_template('unauthorized.html'), 401


conf = json.loads(open('config.json').read())
app.config.update(conf)

db = connect_db()
try:
  db.execute("SELECT * FROM entries")
except sqlite3.OperationalError:
  print "Table 'entries' not found, creating..."
  db.execute(open("entries.sql").read())
  db.commit()
  db.close()
del(db)
