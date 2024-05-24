import os
from diff_match_patch import diff_match_patch

DATA_DIR = "data"
# Temporarily hardcoding the test file
TEST_FILE = "test.md"


def does_file_exist(file_path):
    return os.path.exists(file_path)


def get_file_content(file_path):
    with open(file_path, "r") as file:
        content = file.read()
    return content


def save_file_content(file_path, content):
    with open(file_path, "w") as file:
        file.write(content)


def get_file_path(path):
    # ToDo: Add vault/parent directory sharding
    return f"{DATA_DIR}/{path}"


def get_checksum(content):
    return content


class PatchUtil:
    shadowCache = {}

    def __init__(self):
        pass

    # Prep a shadow cache for the file, return the shadow
    def register(self, key):
        if key not in self.shadowCache and not does_file_exist(
            get_file_path(TEST_FILE)
        ):
            save_file_content(get_file_path(TEST_FILE), "")
            self.shadowCache[key] = ""
        elif key not in self.shadowCache:
            self.shadowCache[key] = get_file_content(get_file_path(TEST_FILE))
        return self.shadowCache[key]

    # Apply patches to the shadow and return a new set of patches to send back to the client
    def applyPatch(self, key, checksum, patch_block):
        dmp = diff_match_patch()
        if key not in self.shadowCache and not does_file_exist(
            get_file_path(TEST_FILE)
        ):
            print("Registering new file")
            self.shadowCache[key] = ""
            save_file_content(get_file_path(TEST_FILE), "")
        elif key not in self.shadowCache:
            self.shadowCache[key] = get_file_content(get_file_path(TEST_FILE))
            print("Register??")
            # We probably shouldn't get here, as a client would 'register' before sending a patch

        # Perform patching
        shadow = self.shadowCache[key]
        incoming_patches = dmp.patch_fromText(patch_block)
        patched_shadow, results = dmp.patch_apply(incoming_patches, shadow)
        if not all(results) or checksum != get_checksum(shadow):
            raise RuntimeError(
                f"Patch failed to apply on shadow! Shadow was {shadow} and checksum was {checksum} for key {key}"
            )
        else:
            print(f"Checksums match {checksum} {get_checksum(shadow)}")

        # Do the final patching
        text = get_file_content(get_file_path(TEST_FILE))
        print(f"Text is {text}")
        patched_text, _ = dmp.patch_apply(incoming_patches, text)
        if patched_text != text:
            save_file_content(get_file_path(TEST_FILE), patched_text)

        # Get patches to send back to client
        outgoing_patches = dmp.patch_make(patched_shadow, patched_text)
        # Update shadow with patched text
        self.shadowCache[key] = patched_text
        print(f"Outgoing patches are {outgoing_patches} to update to {patched_text}")
        # Return patches as a block
        return dmp.patch_toText(outgoing_patches)

    # Called if applyPatch fails
    def getShadowContent(self, key):
        print("Getting shadow content for key:", key)
        if not key in self.shadowCache:
            print("Key not found in shadow cache")
            return ""
        return self.shadowCache[key]
