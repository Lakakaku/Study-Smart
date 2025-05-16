from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/create-quiz')
def create_quiz():
    return render_template("create-quiz.html")

if __name__ == '__main__':
    app.run(debug=True)
