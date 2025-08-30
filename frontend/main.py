from flask import Flask, request
from flask import render_template
app = Flask(name)


@app.route('/')
def index():
    return render_template('index.html')

if name == 'main':
    app.run(debug=True)
