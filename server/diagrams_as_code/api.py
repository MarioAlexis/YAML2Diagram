from flask import Flask
from diagrams_as_code.entrypoint import entrypoint
from diagrams_as_code import ProviderResources

provider_resources_obj = ProviderResources()
app = Flask(__name__)

@app.route("/")
def get_diagram():
    base64_diagram = entrypoint("examples/all-fields.yaml")
    return f"<img style='display:block;' id='base64image' src='data:image/jpeg;base64, {base64_diagram}' />"

@app.route("/provider-resources", methods=['GET'])
def get_providers_resources():
    try:
        resources = provider_resources_obj.provider_resources
        return resources
    except Exception as e:
        print(e)

if __name__ == '__main__':
    app.run()