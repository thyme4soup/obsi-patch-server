import os
from diff_match_patch import diff_match_patch

DATA_DIR = "data"
# Temporarily hardcoding the test file
TEST_FILE = "test.md"


# Define a FileNotFoundError
class FileNotFoundError(Exception):
    pass


def does_file_exist(file_path):
    return os.path.exists(file_path)


def get_file_content(file_path):
    with open(file_path, "r") as file:
        content = file.read()
    return content


def save_file_content(file_path, content):
    # create folder path if it doesn't exist
    print(file_path)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w") as file:
        file.write(content)


def get_file_path(key):
    # ToDo: Add vault/parent directory sharding
    if key[0] is None:
        # No root directory
        return f"{DATA_DIR}/{key[1]}"
    else:
        return f"{DATA_DIR}/{key[0]}/{key[1]}"


def get_checksum(content):
    return content


class PatchUtil:
    # ToDo: Move shadow cache to a persistent store
    shadowCache = {}

    def __init__(self):
        pass

    # Prep a shadow cache for the file, return the shadow
    def register(self, key, content):
        if key not in self.shadowCache and not does_file_exist(get_file_path(key)):
            print(f"Registering new file under {key}")
            save_file_content(get_file_path(key), content)
            self.shadowCache[key] = content
        elif key not in self.shadowCache:
            print(f"Registering existing file under {key}")
            self.shadowCache[key] = content
        return self.shadowCache[key]

    # Apply patches to the shadow and return a new set of patches to send back to the client
    def applyPatch(self, key, checksum, patch_block):
        dmp = diff_match_patch()
        if key not in self.shadowCache and not does_file_exist(get_file_path(key)):
            print("Registering new file")
            self.shadowCache[key] = ""
            save_file_content(get_file_path(key), "")
        elif key not in self.shadowCache:
            raise RuntimeError(f"Key {key} not found in shadow cache")
        # Perform patching
        shadow = self.shadowCache[key]
        incoming_patches = dmp.patch_fromText(patch_block)
        patched_shadow, results = dmp.patch_apply(incoming_patches, shadow)
        if not all(results) or checksum != get_checksum(shadow):
            raise RuntimeError(
                f"Patch failed to apply on shadow! Shadow was {shadow} and checksum was {checksum} for key {key}"
            )

        # Do the final patching
        text = get_file_content(get_file_path(key))
        patched_text, _ = dmp.patch_apply(incoming_patches, text)
        if patched_text != text:
            save_file_content(get_file_path(key), patched_text)

        # Get patches to send back to client
        outgoing_patches = dmp.patch_make(patched_shadow, patched_text)
        # Update shadow with patched text
        self.shadowCache[key] = patched_text
        # Return patches as a block
        return dmp.patch_toText(outgoing_patches)

    # Called if applyPatch fails
    def getShadowContent(self, key):
        if not key in self.shadowCache and not does_file_exist(get_file_path(key)):
            raise FileNotFoundError(f"File not found for key {key}")
        elif not key in self.shadowCache:
            print("Key not found in shadow cache, using live file content")
            self.shadowCache[key] = get_file_content(get_file_path(key))
            return get_file_content(get_file_path(key))
        return self.shadowCache[key]

    def doesRootExist(self, root):
        return os.path.exists(f"{DATA_DIR}/{root}")

    def idempotentCreateAndGetRoot(self, root):
        os.makedirs(f"{DATA_DIR}/{root}", exist_ok=True)
        # Return the recursive tree of the root as a string
        walk = os.walk(f"{DATA_DIR}/{root}")
        # convert the walk into an array of file paths
        paths = []
        for root_dir, dirs, files in walk:
            for file in files:
                path = f"{root_dir}/{file}"
                # remove the data directory from the path
                path = path.replace(f"{DATA_DIR}/{root}/", "")
                paths.append(path)
        return paths
