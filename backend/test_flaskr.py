import os
import unittest
import logging
from flask import json
from flaskr import create_app
from models import db, Question, Category


class TriviaTestCase(unittest.TestCase):
    """This class represents the trivia test case"""

    @classmethod
    def setUpClass(cls):
        """Configure logging once for all tests"""
        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s - %(levelname)s - %(message)s')
        cls.logger = logging.getLogger(__name__)


    def setUp(self):
        """Define test variables and initialize app."""
        self.database_name = "trivia_test"
        self.database_user = "lindameijering"
        self.database_password = "!2503Maart!"
        self.database_host = "localhost:5432"
        self.database_path = f"postgresql://{self.database_user}:{self.database_password}@{self.database_host}/{self.database_name}"

        # Create app with the test configuration
        self.app = create_app({
            "SQLALCHEMY_DATABASE_URI": self.database_path,
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "TESTING": True
            })
        self.client = self.app.test_client()

        # Bind the app to the current context and create all tables
        with self.app.app_context():
            db.create_all()


    def tearDown(self):
        """Executed after each test"""
        with self.app.app_context():
            # Manually delete all questions to avoid foreign key constraint issues
            db.session.query(Question).delete()
            db.session.commit()

            # Now drop all tables
            db.drop_all()

    def test_get_all_categories(self):
        with self.app.app_context():
            populate_db(db=db)
        res = self.client.get("/categories")
        data = json.loads(res.data)

        self.assertEqual(res.status_code, 200)
        self.assertEqual(data["success"], True)
        self.assertTrue(data["total_categories"])
        self.assertTrue(len(data["categories"]))

    def test_no_categories(self):
        res = self.client.get("/categories")
        data = json.loads(res.data)

        self.assertEqual(res.status_code, 404)
        self.assertEqual(data["success"], False)

    def test_get_paginated_questions(self):
        with self.app.app_context():
            populate_db(db=db)
        res = self.client.get("/questions")
        data = json.loads(res.data)

        self.assertEqual(res.status_code, 200)
        self.assertEqual(data["success"], True)
        self.assertTrue(data["total_questions"])
        self.assertTrue(len(data["questions"]))

    def test_404_sent_requesting_beyond_valid_page(self):
        res = self.client.get("/questions?page=1000")
        data = json.loads(res.data)

        self.assertEqual(res.status_code, 404)
        self.assertEqual(data["success"], False)
        self.assertEqual(data["message"], "Resource not found")
        

    def test_delete_question(self):
        with self.app.app_context():
            populate_db(db=db)
            question = Question(question="How do you make a meringue?", answer="By whisking eggwhites fluffy and baking them", category_id=1, difficulty=1)
            question.insert()
            question_id = question.id

        res = self.client.delete(f"/questions/{question_id}")
        data = json.loads(res.data)

        self.assertEqual(res.status_code, 200)
        self.assertEqual(data["success"], True)
        self.assertEqual(data["deleted"], question_id)
        self.assertTrue(len(data["questions"]))
        self.assertTrue(data["total_questions"])

    def test_delete_nonexistent_question(self):
        res = self.client.delete("/questions/913")
        data = json.loads(res.data)

        self.assertEqual(res.status_code, 404)
        self.assertEqual(data["success"], False)
        self.assertEqual(data["message"], "Resource not found")

    def test_create_question(self):
        with self.app.app_context():
            populate_db(db=db)
            new_question = {
                "question": "What is a sachertorte?",
                "answer": "A chocolate cake from the sacher hotel in austria",
                "category_id": 1,
                "difficulty": 2
            }
        res = self.client.post("/questions", json=new_question)
        data = json.loads(res.data)

        self.assertEqual(res.status_code, 200)
        self.assertEqual(data["success"], True)
        self.assertTrue(data["created"])
        self.assertTrue(len(data["questions"]))
        self.assertTrue(data["total_questions"])

    def test_create_incomplete_question(self):
        with self.app.app_context():
            populate_db(db=db)
        incomplete_question = {
            "question": "What is used to fill an éclaire?",
            "answer": "Creme patissiere"
        }
        res = self.client.post("/questions", json=incomplete_question)
        data = json.loads(res.data)

        self.assertEqual(res.status_code, 422)
        self.assertEqual(data["success"], False)
        self.assertEqual(data["message"], "Unprocessable entity")
    
    def test_search_questions(self):
        with self.app.app_context():
            populate_db(db=db)
            question = Question(question="What do mooncakes often contain in the middle?", answer="Cured egg yolk", category_id="1", difficulty=2)
            question.insert()

        search_term = {"searchTerm": "moon"}
        res = self.client.post("/questions/search", json=search_term)
        data = json.loads(res.data)

        self.assertEqual(res.status_code, 200)
        self.assertEqual(data["success"], True)
        self.assertTrue(len(data["questions"]))
        self.assertTrue(data["total_questions"])

    def test_search_nonexistent_questions(self):
        with self.app.app_context():
            populate_db(db=db)
        search_term = {"searchTerm": "fake"}
        res = self.client.post("/questions/search", json=search_term)
        data = json.loads(res.data)

        self.assertEqual(res.status_code, 200)
        self.assertEqual(data["success"], True)
        self.assertEqual(len(data["questions"]), 0)
        self.assertEqual(data["total_questions"], 0)

    def test_search_questions_missing_search_term(self):
        with self.app.app_context():
            populate_db(db=db)
        res = self.client.post("/questions/search", json={})
        data = json.loads(res.data)

        self.assertEqual(res.status_code, 400)
        self.assertEqual(data["success"], False)
        self.assertEqual(data["message"], "Bad request: client error")

    def test_retrieve_questions_from_category(self):
        with self.app.app_context():
            populate_db(db=db)
        res = self.client.get(f"/categories/2/questions")
        data = json.loads(res.data)

        self.assertEqual(res.status_code, 200)
        self.assertEqual(data["success"], True)
        self.assertTrue(len(data["questions"]))
        self.assertTrue(data["total_questions"])
        self.assertEqual(data["current_category"], "Food & Cooking")

    def test_retrieve_questions_category_not_found(self):
        res = self.client.get("/categories/913/questions")
        data = json.loads(res.data)

        self.assertEqual(res.status_code, 404)
        self.assertEqual(data["success"], False)
        self.assertEqual(data["message"], "Resource not found")

    def test_play_quiz(self):
        with self.app.app_context():
            populate_db(db)

        quiz_data = {
            "previous_questions": [],
            "quiz_category": {"type": "Science", "id": 2}
        }
        res = self.client.post("/quizzes", json=quiz_data)
        data = json.loads(res.data)

        self.assertEqual(res.status_code, 200)
        self.assertEqual(data["success"], True)
        self.assertTrue(data["question"])

    def test_play_quiz_no_questions(self):
        quiz_data = {
            "previous_questions": [],
            "quiz_category": {"type": "Science", "id": 913} 
        }
        res = self.client.post("/quizzes", json=quiz_data)
        data = json.loads(res.data)

        self.assertEqual(res.status_code, 200)
        self.assertEqual(data["success"], True)
        self.assertIsNone(data["question"])

def populate_db(db):
    categories = [
        Category(type='Science'),
        Category(type='Food & Cooking')
    ]
    db.session.bulk_save_objects(categories)
    db.session.commit()
    food_category = Category.query.filter_by(type='Food & Cooking').first()
    questions = [
        Question(
            question='What temperature does sugar caramelize at?',
            answer='160°C',
            difficulty=3,
            category_id=food_category.id
        ),
        Question(
            question='Which French pastrys name literally means thousand layers?',
            answer='Mille-feuille',
            difficulty=2,
            category_id=food_category.id
        ),
        Question(
            question='What chemical reaction makes bread rise?',
            answer='Fermentation',
            difficulty=2,
            category_id=food_category.id
        ),
        Question(
            question='What is the main ingredient in traditional French macarons?',
            answer='Almond flour',
            difficulty=1,
            category_id=food_category.id
        ),
        Question(
            question='What does "au bain-marie" mean?',
            answer='To melt something in a Water bath',
            difficulty=3,
            category_id=food_category.id
        ),
        Question(
            question='What makes red velvet cake red traditionally?',
            answer='Cocoa powder reacting with vinegar and buttermilk',
            difficulty=4,
            category_id=food_category.id
        )
    ]
    db.session.bulk_save_objects(questions)
    db.session.commit()
    

# Make the tests conveniently executable
if __name__ == "__main__":
    unittest.main()

# CREATE ROLE student;
