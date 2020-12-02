import os
import csv
import urllib.request
from functools import wraps
import json

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
import pandas as pd
from alpha_vantage.techindicators import TechIndicators
import matplotlib.pyplot as plt

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    users = db.execute("SELECT username, cash FROM users WHERE id = :user_id", user_id=session["user_id"])
    stocks = db.execute( "SELECT symbol, SUM(shares) as total_shares FROM transactions WHERE user_id = :user_id GROUP BY symbol HAVING total_shares > 0", user_id=session["user_id"])
    quotes = {}

    for stock in stocks:
        quotes[stock["symbol"]] = lookup(stock["symbol"])



    username = users[0]["username"]
    cashRemaining = users[0]["cash"]




    return render_template("index.html", username=username, quotes=quotes, stocks=stocks, cashRemaining=cashRemaining)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    if request.method == "POST":
        quote = lookup(request.form.get("symbol"))

        if quote == None:
            return apology("invalid symbol", 400)

        try:
            shares = int(request.form.get("sharesnum"))
        except:
            return apology("shares must be a positive integer", 400)

        if shares <= 0:
            return apology("can't buy less than or 0 shares", 400)

        rows = db.execute("SELECT cash FROM users WHERE id = :user_id", user_id=session["user_id"])

        cash_remaining = rows[0]["cash"]
        price_per_share = quote["price"]


        total_price = price_per_share * shares

        if total_price > cash_remaining:
            return apology("not enough funds")


        db.execute("UPDATE users SET cash = cash - :price WHERE id = :user_id", price=total_price, user_id=session["user_id"])
        db.execute("INSERT INTO transactions (user_id, symbol, shares, price_per_share) VALUES(:user_id, :symbol, :shares, :price)",
                   user_id=session["user_id"],
                   symbol=request.form.get("symbol"),
                   shares=shares,
                   price=price_per_share)

        flash("Bought!")

        return redirect("/")

    else:
        return render_template("buy.html")





@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    transactions = db.execute("SELECT symbol, shares, price_per_share, created_at FROM transactions WHERE user_id =:user_id", user_id=session["user_id"])

    return render_template("history.html", transactions=transactions)





@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""


    session.clear()

    if request.method == "POST":


        if not request.form.get("username"):
            return apology("must provide username", 403)

        elif not request.form.get("password"):
            return apology("must provide password", 403)

        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        session["user_id"] = rows[0]["id"]

        return redirect("/")

    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/login")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""


    if request.method == "POST":
        quote = lookup(request.form.get("symbol"))



        if quote == None:
            return apology("invalid symbol", 400)


        return render_template("quoted.html", quote=quote)

    else:
        return render_template("quote.html")




@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    if request.method == "POST":


        if not request.form.get("username"):
            return apology("must provide username", 400)


        elif not request.form.get("password"):
            return apology("must provide password", 400)

        elif len(request.form.get("password")) <= 5:
            return apology("password too short")


        elif not request.form.get("password") == request.form.get("confirmation"):
            return apology("passwords do not match", 400)


        hash = generate_password_hash(request.form.get("password"))
        new_user_id = db.execute("INSERT INTO users (username, hash) VALUES(:username, :hash)",
                                 username=request.form.get("username"),
                                 hash=hash)

        if not new_user_id:
            return apology("username taken", 400)


        session["user_id"] = new_user_id

        flash("Registered!")


        return redirect("/")


    else:
        return render_template("register.html")




@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":
        quote = lookup(request.form.get("symbol"))

        if quote == None:
            return apology("invalid symbol", 400)

        try:
            shares = int(request.form.get("sharesnum"))
        except:
            return apology("shares must be a positive integer", 400)

        if shares <= 0:
            return apology("can't buy less than or 0 shares", 400)

        rows = db.execute("SELECT cash FROM users WHERE id = :user_id", user_id=session["user_id"])

        cash_remaining = rows[0]["cash"]
        price_per_share = quote["price"]


        total_price = price_per_share * shares

        if total_price > cash_remaining:
            return apology("not enough funds")


        db.execute("UPDATE users SET cash = cash + :price WHERE id = :user_id", price=total_price, user_id=session["user_id"])
        db.execute("INSERT INTO transactions (user_id, symbol, shares, price_per_share) VALUES(:user_id, :symbol, :shares, :price)",
                   user_id=session["user_id"],
                   symbol=request.form.get("symbol"),
                   shares=shares,
                   price=price_per_share)

        flash("Sold!")

        return redirect("/")

    else:
        return render_template("sell.html")




def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
