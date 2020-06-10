import os,requests

from flask import Flask, session,render_template,request,jsonify,redirect
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
def index():
    if session.get('logged_in') is None or False:
        return render_template('login.html')
    return render_template("search.html",user=session['email'])

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get('email')
        password = request.form.get('password')
        x = db.execute('SELECT password FROM users WHERE username = :email', {'email': email}).fetchone()
        if x == None or x['password'] != password:
            return 'Incorrect username or password. Please try again.'
        else:
            session['logged_in'] = True
            session['email'] = email
            return index()
    if request.method == "GET":
          if not session.get('logged_in'):
            return render_template('login.html')
          user=session['email'] 
          return render_template("search.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    if request.method == "POST":
        pwd = request.form.get('password')
        email = request.form.get('email')
        email_check = db.execute("SELECT username FROM users WHERE username = :email",{'email':email}).fetchone()
        if email_check != None:
            return f"Your email {email} already has an account associated with it. Please log in <a href='/login'> here <a>"
        db.execute("INSERT INTO users (username, password) VALUES(:email,:pwd)",{"email":email, "pwd":pwd})
        db.commit()
        return "You have successfuly registered! <a href='/'>Click here to go home</a>"


@app.route("/search", methods=["POST", "GET"])
def search():
    if session.get('logged_in') is None or False:
        return render_template('login.html')
    if request.method == "GET":
        return index()
    search = f"%{request.form.get('search')}%"
    results = db.execute("SELECT * FROM books WHERE title LIKE :search OR author LIKE :search OR isbn LIKE :search",{'search':search}).fetchall()
    return render_template('search.html', results=results,user=session['email'])


@app.route("/<string:isbn>", methods=["POST", "GET"])
def book(isbn):
    if session.get('logged_in') is None or False:
        return render_template('login.html')
    book_data = db.execute("SELECT * FROM books WHERE isbn=:isbn",{'isbn':isbn}).fetchone()
    if book_data == None:
        return "Book not found. Please try again <a href='/search'>Here</a>"
    title = book_data['title']
    author = book_data['author']
    year = book_data['year']
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key":"EOquiAwYzuZQkS4FGKIQ", "isbns":isbn}).json()
    goodreads_avg = res['books'][0]['average_rating']
    goodreads_count = res['books'][0]['ratings_count']
    reviews = db.execute("SELECT * FROM reviews WHERE isbn=:isbn",{'isbn':isbn}).fetchall()
    return render_template("book.html", title=title, author= author, year=year, isbn=isbn, rating=goodreads_avg, count=goodreads_count, reviews=reviews, user=session['email'])

@app.route("/submit", methods=["POST"])
def submit():
        if session.get('logged_in') is None or False:
            return render_template('login.html')
        email = session['email']
        isbn = request.form.get('isbn')
        email_check = db.execute("SELECT username FROM reviews WHERE username = :email and isbn = :isbn",{'email':email,'isbn':isbn}).fetchone()
        if email_check != None:
            return f"Your email {email} has already submitted a review for this book. Please review other books <a href='/search'> here <a>"
        rating = request.form.get('rating')
        review = request.form.get('review')
        db.execute("INSERT INTO reviews (username, isbn, rating, review) VALUES (:email, :isbn, :rating, :review)", {'email':email, 'isbn':isbn, 'rating':rating, 'review':review})
        db.commit()
        return "You have successfuly added a review! <a href='/'>Click here to go home</a>"

@app.route("/api/<string:isbn>")
def api(isbn):
    book = db.execute("SELECT * FROM books WHERE isbn=:isbn",{'isbn':isbn}).fetchone()
    if book is None:
        return  '<h1> 404 Not Found </h1>' 
    title = book['title']
    author = book['author']
    year = book['year']
    isbn = isbn
    review_count = db.execute("SELECT COUNT(*) FROM reviews WHERE isbn=:isbn",{'isbn':isbn}).fetchone()[0]
    average_score = db.execute("SELECT AVG(reviews.rating) FROM reviews WHERE isbn=:isbn",{'isbn':isbn}).fetchone()[0]
    if average_score != None:
        average_score = round(float(average_score),2)
    temp_dic = {"title": title, "author":author, "year": year,"isbn":isbn, "review_count":review_count, "average_score": average_score }
    print(temp_dic)
    return jsonify(temp_dic)


@app.route("/logout")
def logout():
    session.clear()
    return redirect('/login')