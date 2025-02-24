from flask import Flask, request, abort, jsonify
from flask_cors import CORS
import random

from models import setup_db, Question, Category, db

QUESTIONS_PER_PAGE = 10


def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.debug = True

    if test_config is None:
        setup_db(app)
    else:
        database_path = test_config.get('SQLALCHEMY_DATABASE_URI')
        setup_db(app, database_path=database_path)

    CORS(app, resources={r"/api/*": {"origins": "*"}})

    with app.app_context():
        db.create_all()

    @app.after_request
    def after_request(response):
        response.headers.add('Access-Control-Allow-Headers',
                             'Content-Type, Authorization')
        response.headers.add('Access-Control-Allow-Headers',
                             'GET, POST, PATCH, DELETE, OPTIONS')
        return response

    @app.route("/categories")
    def get_all_categories():
        try:
            categories = get_formatted_categories()
            if len(categories) == 0:
                abort(404)

            return jsonify({
                "success": True,
                "categories": categories,
                "total_categories": len(categories)
            })
        except:
            abort(404)

    @app.route("/questions")
    def retrieve_questions():
        selection = Question.query.order_by(Question.id).all()
        current_questions = paginate_questions(request, selection)

        categories = get_formatted_categories()

        if len(current_questions) == 0:
            abort(404)

        return jsonify({
            "success": True,
            "questions": current_questions,
            "total_questions": len(selection),
            "current_category": None,
            "categories": categories,
            "current_page": request.args.get('page', 1, type=int)
        })

    @app.route("/questions/<int:question_id>", methods=["DELETE"])
    def delete_question(question_id):
        question = Question.query.filter(
            Question.id == question_id).one_or_none()

        if question is None:
            abort(404)

        question.delete()
        selection = Question.query.order_by(Question.id).all()
        current_questions = paginate_questions(request, selection)

        return jsonify(
            {
                "success": True,
                "deleted": question_id,
                "questions": current_questions,
                "total_questions": len(Question.query.all()),
            }
        )

    @app.route("/questions", methods=["POST"])
    def create_question():
        body = request.get_json()

        new_question = body.get("question", None)
        new_answer = body.get("answer", None)
        new_category = body.get("category_id", None)
        new_difficulty = body.get("difficulty", None)

        try:
            question = Question(question=new_question, answer=new_answer,
                                category_id=new_category, difficulty=new_difficulty)
            question.insert()

            selection = Question.query.order_by(Question.id).all()
            current_questions = paginate_questions(request, selection)

            return jsonify(
                {
                    "success": True,
                    "created": question.id,
                    "questions": current_questions,
                    "total_questions": len(Question.query.all()),
                }
            )

        except:
            abort(422)

    @app.route('/questions/search', methods=['POST'])
    def search_questions():
        body = request.get_json()
        search_term = body.get("searchTerm", None)
        if search_term == None:
            abort(400)
        questions = Question.query.filter(
            Question.question.ilike(f'%{search_term}%')).all()

        formatted_questions = [question.format() for question in questions]

        return jsonify(
            {
                "success": True,
                "questions": formatted_questions,
                "total_questions": len(formatted_questions),
                "current_category": ''
            }
        )

    @app.route("/categories/<int:category>/questions")
    def retrieve_questions_from_category(category):
            category = Category.query.filter(
                Category.id == category).one_or_none()
            print(category)

            if category is None:
                abort(404)

            questions = Question.query.filter(
                Question.category_id== category.id).all()
            formatted_questions = [question.format() for question in questions]
            current_category = category.type

            return jsonify(
                {
                    "success": True,
                    "questions": formatted_questions,
                    "total_questions": len(Question.query.all()),
                    "current_category": current_category
                }
            )

    @app.route('/quizzes', methods=['POST'])
    def play_quiz():
        try:
            body = request.get_json()

            previous_questions = body.get('previous_questions', [])
            quiz_category = body.get('quiz_category', None)

            query = Question.query.filter(
                Question.id.notin_(previous_questions)
            )

            if quiz_category and quiz_category['id'] != 0:
                        query = query.filter(Question.category_id == quiz_category['id'])

            available_questions = query.all()
            next_question = random.choice(
                available_questions) if available_questions else None

            formatted_question = next_question.format() if next_question else None

            return jsonify({
                'success': True,
                'question': formatted_question
            })
        except Exception as e:
            abort(400, description=str(e))

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            "success": False,
            "error": 404,
            "message": "Resource not found"
        }), 404

    @app.errorhandler(422)
    def unprocessable_entity(error):
        return jsonify({
            "success": False,
            "error": 422,
            "message": "Unprocessable entity"
        }), 422

    @app.errorhandler(500)
    def server_error(error):
        return jsonify({
            "success": False,
            "error": 500,
            "message": "Internal server error"
        }), 500

    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            "success": False,
            "error": 400,
            "message": "Bad request: client error"
        }), 400
    return app


def paginate_questions(request, selection):
    page = request.args.get("page", 1, type=int)
    start = (page - 1) * QUESTIONS_PER_PAGE
    end = start + QUESTIONS_PER_PAGE

    questions = [question.format() for question in selection]
    current_questions = questions[start:end]

    return current_questions


def get_formatted_categories():
    categories = Category.query.all()

    formatted_categories = {
        category.id: category.format()['type']
        for category in categories
    }
    return formatted_categories


# $env:FLASK_APP = "flaskr"
# $env:FLASK_ENV = "development"
# flask run

# psql -U your_username -d your_database_name -f trivia.psql
