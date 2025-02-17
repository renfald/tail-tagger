import os
import json

class FileOperations:
    """Handles file system operations for the image tagger."""

    staging_folder_path = None  # Class variable for staging folder

    def __init__(self):
        pass

    def get_workfile_path(self, folder_path):
        """Generates a valid workfile path based on the image folder path."""
        filename_safe_string = folder_path.replace(os.sep, '_').replace(':', '_') + ".json"
        return os.path.join(self.staging_folder_path, filename_safe_string)

    def update_workfile(self, last_folder_path, image_path, tags):
        """Updates the workfile with the tags for the given image."""
        if last_folder_path:  # Only save if a folder has been loaded.
            workfile_path = self.get_workfile_path(last_folder_path)

            tag_names = [tag.name for tag in tags]  # Extract tag names

            try:
                with open(workfile_path, 'r+', encoding='utf-8') as f:
                    data = json.load(f)
                    data["image_tags"][image_path] = tag_names  # Use extracted tag names
                    f.seek(0)
                    json.dump(data, f, indent=2)
                    f.truncate()

            except FileNotFoundError:
                print(f"Error: Workfile not found at {workfile_path}.")
            except json.JSONDecodeError:
                print(f"Error: Corrupted workfile at {workfile_path}.")
    
    def gather_all_tags(self, folder_path):
        """Gathers tag data for all images in the specified folder."""
        all_tags = {}
        workfile_path = self.get_workfile_path(folder_path)
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']
        image_paths = []

        for filename in os.listdir(folder_path):
            if any(filename.lower().endswith(ext) for ext in image_extensions):
                image_path = os.path.join(folder_path, filename)
                image_paths.append(image_path)

        try:
            with open(workfile_path, 'r', encoding='utf-8') as f:
                workfile_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            workfile_data = {"image_tags": {}}

        for image_path in image_paths:
            loaded_tags = []

            if workfile_data:
                if image_path in workfile_data["image_tags"]:
                    loaded_tags = workfile_data["image_tags"][image_path]
                    print(f"  Loaded tags from workfile for {image_path}: {loaded_tags}")

            if not loaded_tags:
                tag_file_path_no_ext = os.path.splitext(image_path)[0]
                tag_file_path_txt = tag_file_path_no_ext + ".txt"
                tag_file_path_ext_txt = image_path + ".txt"

                if os.path.exists(tag_file_path_txt):
                    tag_file_to_use = tag_file_path_txt
                elif os.path.exists(tag_file_path_ext_txt):
                    tag_file_to_use = tag_file_path_ext_txt
                else:
                    tag_file_to_use = None

                if tag_file_to_use:
                    print(f"  Loading tags from .txt for {image_path}")
                    try:
                        with open(tag_file_to_use, 'r', encoding='utf-8') as tag_file:
                            tag_content = tag_file.readline().strip()
                            loaded_tags = [tag.strip() for tag in tag_content.split(',')]
                    except Exception as e:
                        print(f"  Error reading tag file {tag_file_to_use}: {e}")

            all_tags[image_path] = loaded_tags

        return all_tags

    def load_tags_for_image(self, image_path, last_folder_path):
        """Loads tags for a single image, prioritizing workfile then .txt file."""
        loaded_tags_from_workfile = False
        workfile_path = self.get_workfile_path(last_folder_path)

        loaded_tags = [] # Initialize here

        if os.path.exists(workfile_path):
            try:
                with open(workfile_path, 'r', encoding='utf-8') as f:
                    workfile_data = json.load(f)
                    image_key = image_path
                    if image_key in workfile_data["image_tags"]:
                        loaded_tags = workfile_data["image_tags"][image_key]
                        print(f"  Loaded tags from workfile: {loaded_tags}")
                        loaded_tags_from_workfile = True
            except FileNotFoundError:
                print(f"  Workfile not found (though existence was just checked).")
            except json.JSONDecodeError:
                print(f"  Error reading workfile. Falling back to .txt or empty.")

        if not loaded_tags_from_workfile:
            tag_file_path_no_ext = os.path.splitext(image_path)[0]
            tag_file_path_txt = tag_file_path_no_ext + ".txt"
            tag_file_path_ext_txt = image_path + ".txt"


            if os.path.exists(tag_file_path_txt):
                tag_file_to_use = tag_file_path_txt
            elif os.path.exists(tag_file_path_ext_txt):
                tag_file_to_use = tag_file_path_ext_txt
            else:
                tag_file_to_use = None

            if tag_file_to_use:
                print(f"  Loading tags from: {tag_file_to_use}")
                try:
                    with open(tag_file_to_use, 'r', encoding='utf-8') as tag_file:
                        tag_content = tag_file.readline().strip()
                        loaded_tags = [tag.strip() for tag in tag_content.split(',')]
                        print(f"  Loaded tags from .txt file: {loaded_tags}")
                except Exception as e:
                    print(f"  Error reading tag file: {e}")
                    loaded_tags = [] # Ensure loaded_tags is empty on error.
            else:
                print("  No tag file found for this image.")
                loaded_tags = [] # Ensure loaded_tags is empty if no file is found.
        return loaded_tags


    def export_tags(self, parent, last_folder_path):
        """Handles the export process: prompts for export directory, gathers tags, and writes files."""
        from PySide6.QtWidgets import QFileDialog
        import sys
        import subprocess

        # Create the 'output' directory if it doesn't exist
        output_dir = os.path.join(os.getcwd(), "output")
        if not os.path.isdir(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        # Get the export directory from the user.
        export_dir = QFileDialog.getExistingDirectory(parent, "Select Export Directory", output_dir)

        if export_dir:  # Proceed only if the user selected a directory.
            export_dir = os.path.normpath(export_dir)
            print(f"Exporting tags to: {export_dir}")

            all_tags = self.gather_all_tags(last_folder_path) #we assume if they are exporting, that they have opened a dir

            for image_path, tags in all_tags.items():
                filename = os.path.basename(image_path)
                base_filename, _ = os.path.splitext(filename)  # Remove extension
                txt_filename = base_filename + ".txt"
                txt_filepath = os.path.join(export_dir, txt_filename)

                try:
                    with open(txt_filepath, 'w', encoding='utf-8') as f:
                        f.write(", ".join(tags))  # Join tags with comma and space.
                    print(f"  Wrote tags for {filename} to {txt_filepath}")
                except Exception as e:
                    print(f"  Error writing to {txt_filepath}: {e}")
                    # Consider showing an error message to the user (QMessageBox).

            # Open the export directory in the file explorer.
            if sys.platform == 'win32':
                os.startfile(export_dir)
            elif sys.platform == 'darwin':  # macOS
                subprocess.Popen(['open', export_dir])
            else:  # Linux and other Unix-like
                subprocess.Popen(['xdg-open', export_dir]) # Try xdg-open (common on Linux)
        else:
            print("Export cancelled by user.")

    def create_default_workfile(self, folder_path):
        """Creates a default workfile if one doesn't exist."""
        workfile_path = self.get_workfile_path(folder_path)
        if not os.path.exists(workfile_path):
            try:
                with open(workfile_path, 'w', encoding='utf-8') as f:
                    json.dump({"image_tags": {}}, f)
                print(f"Created default workfile at {workfile_path}")
            except Exception as e:
                print(f"Error creating default workfile: {e}")