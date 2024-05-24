from flask import Flask, request, jsonify
import patch_util
import uuid
from flask_cors import cross_origin

# Create a Flask app with debug mode enabled
app = Flask(__name__)
app.config["DEBUG"] = True
# Run with `flask run --debugger --reload`

patcher = patch_util.PatchUtil()


def get_patch_response(code, patch, checksum, content=None):
    return jsonify(
        {"status": code, "patch": patch, "checksum": checksum, "content": content}
    )


def get_register_response(code, content=None, user_id=None):
    return jsonify({"status": code, "content": content, "userId": user_id})


@app.route("/register", methods=["GET"])
@cross_origin()
def register():
    data = request.json
    user_id = uuid.uuid4()
    print(data)
    if not data:
        return get_register_response(400, "No request body found", "")
    if "path" not in data:
        return get_register_response(400, "Path not found", "")
    if "userId" in data:
        user_id = data["userId"]
    else:
        user_id = uuid.uuid4()
    path = data["path"]

    server_shadow = patcher.register((path, user_id))

    return get_register_response(200, server_shadow, user_id)


@app.route("/patch", methods=["POST"])
@cross_origin()
def applyPatch():
    data = request.json
    print(data)
    if "path" not in data:
        return get_patch_response(400, "", "", "Path not found")
    elif "checksum" not in data:
        return get_patch_response(400, "", "", "Checksum not found")
    elif "patch" not in data:
        return get_patch_response(400, "", "", "Patch not found")
    elif "userId" not in data:
        return get_patch_response(400, "", "", "User ID not found")
    elif "secretKey" not in data:
        return get_patch_response(400, "", "", "Secret key not found")

    path = patch_util.TEST_FILE
    checksum = data["checksum"]
    patch_block = data["patch"]
    key = (path, data["userId"])

    try:
        shadow_content = patcher.getShadowContent(key)
        outgoing_patches = patcher.applyPatch(key, checksum, patch_block)
        return get_patch_response(200, outgoing_patches, shadow_content, None)
    except RuntimeError as e:
        print(e)
        return get_patch_response(409, "", "", patcher.getShadowContent(key))


# Run the app
if __name__ == "__main__":
    app.run()
