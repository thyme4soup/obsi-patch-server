from flask import Flask, request, jsonify
import patch_util
import uuid
from flask_cors import cross_origin

# Create a Flask app with debug mode enabled
app = Flask(__name__)
app.config["DEBUG"] = True
# Run with `flask run --debugger --reload`

API_VERSION = "v1"
patcher = patch_util.PatchUtil()


def get_patch_response(code, patch, checksum, content=None):
    resp = {"status": code, "patch": patch, "checksum": checksum, "content": content}
    print(resp)
    return jsonify(resp)


def get_register_response(code, content=None, user_id=None):
    resp = {"status": code, "content": content, "userId": user_id}
    print(resp)
    return jsonify(resp)


def get_root_response(code, root, tree=None):
    resp = {"status": code, "root": root, "tree": tree}
    print(resp)
    return jsonify(resp)


@app.route(f"/{API_VERSION}/register", methods=["POST"])
@cross_origin()
def register():
    data = request.json
    user_id = uuid.uuid4()
    if not data:
        return get_register_response(400, "No request body found", "")
    if "path" not in data:
        return get_register_response(400, "Path not found", "")
    if "root" not in data:
        return get_register_response(400, "Root not found", "")
    if "userId" in data and data["userId"] is not None and data["userId"] != "null":
        user_id = data["userId"]
    else:
        user_id = str(uuid.uuid4())
    path = data["path"]
    root = data.get("root", None)
    content = data.get("content", "")

    try:
        server_shadow = patcher.register((root, path, user_id), content)
        return get_register_response(200, server_shadow, user_id)
    except patch_util.FileDeletedError as e:
        print(e)
        return get_register_response(409, "File is deleted", user_id)


@app.route(f"/{API_VERSION}/patch", methods=["POST"])
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

    path = data["path"]
    checksum = data["checksum"]
    patch_block = data["patch"]
    root = data.get("root", None)
    key = (root, path, data["userId"])

    # Check for root
    if root and not patcher.doesRootExist(root):
        print(
            f"Client {data['userId']} tried to access root {root} which does not exist"
        )
        return get_patch_response(404, "", "", "Root does not exist")

    try:
        shadow_content = patcher.getShadowContent(key)
        outgoing_patches = patcher.applyPatch(key, checksum, patch_block)
        return get_patch_response(
            200, outgoing_patches, patch_util.get_checksum(shadow_content), None
        )
    except RuntimeError as e:
        print(e)
        return get_patch_response(409, "", "", patcher.getShadowContent(key))
    except patch_util.FileDeletedError as e:
        print(e)
        return get_patch_response(409, "", "", "File is deleted")
    except patch_util.FileNotFoundError as e:
        print(e)
        return get_patch_response(404, "", "", "File not found")
    except Exception as e:
        print(e)
        raise e


@app.route(f"/{API_VERSION}/root", methods=["POST"])
@cross_origin()
def root():
    data = request.json
    if "userId" not in data:
        return get_register_response(400, "User ID not provided", "")
    if "secretKey" not in data:
        return get_register_response(400, "Secret key not provided", "")
    if (
        "root" not in data
        or data["root"] is None
        or data["root"] == "null"
        or data["root"] == "undefined"
    ):
        print("Create root")
        root = uuid.uuid4()
    else:
        root = data["root"]

    tree = patcher.idempotentCreateAndGetRoot(root)
    return get_root_response(200, root, tree)


@app.route(f"/{API_VERSION}/delete", methods=["POST"])
@cross_origin()
def delete():
    data = request.json
    if "userId" not in data:
        return get_register_response(400, "User ID not provided", "")
    if "secretKey" not in data:
        return get_register_response(400, "Secret key not provided", "")
    if "path" not in data:
        return get_register_response(400, "Path not provided", "")
    if "root" not in data:
        return get_register_response(400, "Root not provided", "")

    path = data["path"]
    root = data["root"]
    key = (root, path, data["userId"])
    try:
        shadow_content = patcher.getShadowContent(key)
        patcher.delete(key)
        return jsonify({"status": 200, "content": shadow_content})
    except patch_util.FileNotFoundError as e:
        print(e)
        return jsonify({"status": 404, "content": "File not found"})


# Run the app
if __name__ == "__main__":
    app.run(host="0.0.0.0")
