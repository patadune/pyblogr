# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, redirect, url_for, make_response, session, abort, g
import sqlite3, os
from ConfigParser import ConfigParser
from datetime import datetime
from markdown import markdown
import hashlib




DATABASE = 'master.sqlite'
DEBUG = True
SECRET_KEY = 'fa26be19de6bff93f70bc2308434e4a440bbad02' # Used by Flask sessions, keep it here !
SALT = 'L8m3DTnYdT5EzcWDwxYP'                           # For storing password (username+salt+password)







def connect_db():
  db = sqlite3.connect(app.config['DATABASE'])
  db.row_factory = sqlite3.Row
  return db

def formatDate(isodate):
  
  monthsFR = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre']
  
  timehandler = datetime.strptime(isodate, "%Y-%m-%dT%H:%M:%S")
  month = timehandler.month - 1
  return unicode(timehandler.strftime("%d "+monthsFR[month]+" %Y à %Hh%M"), 'utf-8')

def require_login():
  if not session.has_key('username'):
    abort(401)
  return 0




app = Flask(__name__)
app.config.from_object(__name__)



db = connect_db()
try:
  db.execute("SELECT * FROM entries")
except sqlite3.OperationalError:
  print "Table 'entries' not found, creating..."
  db.execute(open("entries.sql").read())
  db.commit()
  db.close()
del(db)



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

@app.route('/add', methods=['POST', 'GET'])
def add_post():
  require_login()
  error = None
  if request.method == 'POST':
      title = request.form['title']
      content = markdown(request.form['content'])
      timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
      if content:
        cur = g.db.cursor()
        cur.execute('INSERT INTO entries(type, title, content, datetime) VALUES (?, ?, ?, ?)', ("text", title, content, timestamp))
        g.db.commit()
        return render_template('done_add_post.html', id=cur.lastrowid)
      
      error = 'You missed a field.'
      
  return render_template('add_post.html', error=error)

@app.route('/del')
def list_posts_deletion():
  require_login()
  cur = g.db.cursor()
  cur.execute('SELECT rowid, title FROM entries')
  posts = cur.fetchall()
  return render_template('del_post.html', posts=posts)

@app.route('/del/<int:postId>')
def delete_post(postId):
  require_login()
  cur = g.db.cursor()
  cur.execute('DELETE FROM entries WHERE rowid=?', (postId,))
  g.db.commit()
  return redirect(url_for('list_posts_deletion'))

@app.route('/search')
@app.route('/search/')
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
    return redirect(url_for('index'))
  if request.method == "POST":
    username = request.form['username']
    password = request.form['password']
    cur = g.db.cursor()
    cur.execute("SELECT * FROM users WHERE username=?", (username,))
    login_info = cur.fetchone()
    if login_info == None:
      return 'wrong credentials, try again'
    auth_string = hashlib.sha1(username+app.config['SALT']+password).hexdigest()
    if auth_string == login_info['password']:
      session['username'] = username
      return redirect(url_for('admin'))
  return render_template('login.html')
  
@app.route('/logout')
def logout():
  session.pop('username', None)
  return redirect(url_for('index'))

@app.route('/admin')
def admin():
  return render_template('admin.html', session=session)

if __name__ == '__main__':
  app.run()
