# 10-Finger Typing System Project
This is a web-based application designed to help users learn and improve their typing skills using the 10-finger typing method. The system tracks typing accuracy, speed (characters per minute), and mistakes, providing personalized feedback to help users enhance their skills.<br><br>

## Features
<ul>
<li><b>User Registration & Login:</b> Secure user authentication with hashed passwords.</li>
<li><b>Typing Accuracy Tracking:</b> Calculates and stores accuracy percentages for each typing session.</li>
<li><b>Characters Per Minute (CPM):</b> Measures typing speed.</li>
<li><b>Error Logging:</b> Records incorrect key presses for detailed analysis.</li>
<li><b>Real-time Feedback:</b> Highlights mistakes during the typing session.</li>
<li><b>Database Integration:</b> Tracks user performance and stores session data using PostgreSQL.</li>
</ul><br>

## Technologies Used
<ul>
<li><b>Backend:</b> Flask (Python 3.12)</li>
<li><b>Frontend:</b> HTML, CSS, JavaScript</li>
<li><b>Database:</b> PostgreSQL</li>
<li><b>ORM:</b> SQLAlchemy</li>
</ul><br>

## Configure PostgreSQL

1.) <b>Create a PostgreSQL Database:</b>
<ul><li>Open PG Admin and create a new database, e.g., <code>typing_system</code></li></ul>

2.) <b>Initialize the Database:</b>
<ul><li>Run the module.py script to create all tables and their relationships:</li>
<li>This will set up the schema, relationships, and all primary/foreign keys automatically.</li></ul><br>

## Run the Application

1.) Initialize the database: <code>python module.py</code><br><br>
2.) Start the Flask server: <code>python app.py</code><br><br>
3.) Open your brower and navigate to: <code>http://127.0.0.1:5000</code><br><br><br>

## Usage Instructions

1.) <b>Register:</b> Create a new account.<br><br>
2.) <b>Login:</b> Use your credentials to log in.<br><br>
3.) <b>Choose a Text:</b> Select a text to start your typing session<br><br>
4.) <b>Start Typing:</b> Begin practicing and receive real-time feedback.<br><br>
5.) <b>Review Performance:</b> Check your CPM, accuracy, and mistakes in the database<br><br><br>

## License

This priject is licensed under the MIT License.
