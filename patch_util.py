import hashlib
import os
import shelve
from diff_match_patch import diff_match_patch

DATA_DIR = "/data"
# Temporarily hardcoding the test file
TEST_FILE = "test.md"

# Create the data directory if it doesn't exist
os.makedirs(DATA_DIR, exist_ok=True)


# Define a FileNotFoundError
class FileNotFoundError(Exception):
    pass


# Define a FileDeletedError
class FileDeletedError(Exception):
    pass


def does_file_exist(file_path):
    return os.path.exists(file_path)


def is_file_deleted(file_path):
    file_name = file_path.split("/")[-1]
    parent_dir = "/".join(file_path.split("/")[0:-1])
    delete_file_path = parent_dir + "/DELETED_" + file_name
    if file_name.startswith("DELETED_"):
        return True
    elif os.path.exists(delete_file_path):
        return True
    elif os.path.exists(file_path):
        return False
    else:
        return False


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


def delete_file(file_path):
    file_name = file_path.split("/")[-1]
    parent_dir = "/".join(file_path.split("/")[0:-1])
    if file_name.startswith("DELETED_"):
        # idempotent delete
        return True
    elif os.path.exists(file_path):
        # Rename the file to DELETED_<file_name>
        os.rename(file_path, parent_dir + "/DELETED_" + file_name)
    else:
        raise FileNotFoundError(f"File {file_path} not found")


def get_checksum(content):
    # calculate checksum as a simple hash
    checksum = hashlib.md5(content.encode()).hexdigest()
    return checksum


class PatchUtil:
    # ToDo: Move shadow cache to a persistent store
    shadowPath = f"{DATA_DIR}/shadow"

    def __init__(self):
        pass

    # Prep a shadow cache for the file, return the shadow
    def register(self, key, content):
        with shelve.open(self.shadowPath) as shadow:
            if is_file_deleted(get_file_path(key)):
                raise FileDeletedError(f"File {key} is deleted")
            elif str(key) not in shadow and not does_file_exist(get_file_path(key)):
                print(f"Registering new file under {key}")
                save_file_content(get_file_path(key), content)
                shadow[str(key)] = content
            elif str(key) not in shadow:
                print(f"Registering existing file under {key}")
                shadow[str(key)] = content
            return shadow[str(key)]

    def delete(self, key):
        if is_file_deleted(get_file_path(key)):
            raise FileDeletedError(f"File {key} is deleted")
        delete_file(get_file_path(key))
        with shelve.open(self.shadowPath) as shadow:
            shadow.pop(str(key), None)
        return True

    # Apply patches to the shadow and return a new set of patches to send back to the client
    def applyPatch(self, key, checksum, patch_block):
        # Load the shadow cache

        with shelve.open(self.shadowPath) as shadowCache:
            dmp = diff_match_patch()
            if is_file_deleted(get_file_path(key)):
                raise FileDeletedError(f"File {key} is deleted")
            elif str(key) not in shadowCache and not does_file_exist(get_file_path(key)):
                print("Registering new file")
                shadowCache[key] = ""
                save_file_content(get_file_path(key), "")
            elif str(key) not in shadowCache:
                raise RuntimeError(f"Key {key} not found in shadow cache")
            # Perform patching
            shadow = shadowCache[str(key)]
            incoming_patches = dmp.patch_fromText(patch_block)
            patched_shadow, results = dmp.patch_apply(incoming_patches, shadow)
            if not all(results) or checksum != get_checksum(shadow):
                raise RuntimeError(
                    f"Patch failed to apply on shadow! Shadow was {get_checksum(shadow)} and checksum was {checksum} for key {key}"
                )

            # Do the final patching
            text = get_file_content(get_file_path(key))
            patched_text, _ = dmp.patch_apply(incoming_patches, text)
            if patched_text != text:
                save_file_content(get_file_path(key), patched_text)

            # Get patches to send back to client
            outgoing_patches = dmp.patch_make(patched_shadow, patched_text)
            # Update shadow with patched text
            shadowCache[str(key)] = patched_text
            # Return patches as a block
            return dmp.patch_toText(outgoing_patches)

    # Called if applyPatch fails
    def getShadowContent(self, key):
        with shelve.open(self.shadowPath) as shadow:
            if not str(key) in shadow and not does_file_exist(get_file_path(key)):
                raise FileNotFoundError(f"File not found for key {key}")
            elif not str(key) in shadow:
                print("Key not found in shadow cache, using live file content")
                shadow[str(key)] = get_file_content(get_file_path(key))
                return get_file_content(get_file_path(key))
            return shadow[str(key)]

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
                path = path.replace(f"\\", "/")
                path = path.replace(f"{DATA_DIR}/{root}/", "")
                paths.append(path)
        return paths

    def getChecksum(self, key):
        with shelve.open(self.shadowPath) as shadow:
            return get_checksum(shadow[str(key)])
