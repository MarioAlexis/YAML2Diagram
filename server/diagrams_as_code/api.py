from flask import Flask
from diagrams_as_code.entrypoint import entrypoint
app = Flask(__name__)

@app.route("/")
def get_diagram():
    base64_diagram = entrypoint("examples/all-fields.yaml")
    return f"<img style='display:block;' id='base64image' src='data:image/jpeg;base64, {base64_diagram}' />"