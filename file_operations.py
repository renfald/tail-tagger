import os
import json
import csv

class FileOperations:
    """Handles file system operations for the image tagger."""

    staging_folder_path = None  # Class variable for staging folder

    def __init__(self):
        pass
        
    def _load_json_file(self, file_path, default_value=None, create_if_missing=True):
        """Helper method to load JSON data from a file with standardized error handling.
        
        Args:
            file_path (str): Path to the JSON file to load
            default_value: Value to return if the file is not found or has invalid JSON
            create_if_missing (bool): Whether to create the file with default_value if not found
            
        Returns:
            The loaded JSON data, or default_value if loading fails
        """
        if default_value is None:
            default_value = {}
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"File not found: {file_path}. Using default value.")
            if create_if_missing:
                print(f"Creating new file at {file_path} with default data.")
                self._save_json_file(file_path, default_value)
            return default_value
        except json.JSONDecodeError:
            print(f"Error decoding JSON in {file_path}. Using default value.")
            return default_value
        except Exception as e:
            print(f"Error loading JSON file {file_path}: {e}")
            return default_value
            
    def _save_json_file(self, file_path, data, indent=2):
        """Helper method to save JSON data to a file with standardized error handling.
        
        Args:
            file_path (str): Path to save the JSON file
            data: Data to save as JSON
            indent (int): Indentation level for pretty-printing
            
        Returns:
            bool: True if saving succeeded, False otherwise
        """
        try:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=indent)
            return True
        except Exception as e:
            print(f"Error saving JSON to {file_path}: {e}")
            return False

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
                        
                        # txt files may have spaces in tag names, so convert them to underscores before loading to workfile or model
                        for i in range(len(loaded_tags)):
                            loaded_tags[i] = FileOperations.convert_spaces_to_underscores(loaded_tags[i])
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
                        spaced_tags = [FileOperations.convert_underscores_to_spaces(tag) for tag in tags] # TODO: may need to have it configurable
                        f.write(", ".join(spaced_tags))
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

    def load_favorites(self):
        """Loads the ordered list of favorite tag names from favorites.json."""
        favorites_file_path = os.path.join(os.getcwd(), "data", "favorites.json")
        data = self._load_json_file(
            favorites_file_path, 
            default_value={"favorites": []},
            create_if_missing=True
        )
        return data.get("favorites", [])
        
    def save_favorites(self, favorite_tags):
        """Saves the ordered list of favorite tag names to favorites.json."""
        favorites_file_path = os.path.join(os.getcwd(), "data", "favorites.json")
        tag_names = [tag.name for tag in favorite_tags] # Extract names!
        self._save_json_file(favorites_file_path, {"favorites": tag_names})

    @staticmethod
    def convert_underscores_to_spaces(tag_name):
        """Converts underscores in a tag name to spaces for display."""
        return tag_name.replace('_', ' ')

    @staticmethod
    def convert_spaces_to_underscores(tag_name):
        """Converts spaces in a tag name to underscores for storage."""
        return tag_name.replace(' ', '_')

    def add_tag_to_csv(self, csv_path, tag_name):
        """
        Appends a new tag to the tags-list.csv file, ensuring it's on a new line.
        """
        try:
            # 1. Check if the file exists and is not empty. If not, create with header
            if not os.path.exists(csv_path) or os.path.getsize(csv_path) == 0:
                with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                    csv_writer = csv.writer(csvfile)
                    csv_writer.writerow(["id", "name", "category", "post_count"]) # Write header
                print(f"Created new CSV file with header at {csv_path}")

            # 2. Check if the file already ends with a newline.
            with open(csv_path, 'rb') as csvfile:
                csvfile.seek(0, os.SEEK_END) # Go to the end of the file
                if csvfile.tell() == 0:
                    ends_with_newline = True
                else:
                    csvfile.seek(-1, os.SEEK_END)
                    ends_with_newline = csvfile.read(1) == b'\n'

            # 3. Open in append mode, add newline if needed, and write the new tag.
            with open(csv_path, 'a', newline='', encoding='utf-8') as csvfile:
                csv_writer = csv.writer(csvfile)
                if not ends_with_newline:
                    csvfile.write('\n') # Add a newline if it doesn't end with one
                csv_writer.writerow(["", tag_name, "9", "0"])  # Write new row
            print(f"New tag '{tag_name}' added to CSV at {csv_path}")
            return True
        except Exception as e:
            print(f"Error writing to CSV: {e}")
            return False
        
    def load_usage_data(self):
        """Loads tag usage data from usage_data.json.
        Returns a dictionary of tag names to usage counts.
        Returns an empty dict if file not found or loading fails.
        """
        usage_data_path = os.path.join(os.getcwd(), "data", "usage_data.json")
        data = self._load_json_file(
            usage_data_path, 
            default_value={},
            create_if_missing=True
        )
        print(f"  Loaded usage data from: {usage_data_path}")
        return data
    
    def save_usage_data(self, usage_data):
        """Saves tag usage data to usage_data.json."""
        usage_data_path = os.path.join(os.getcwd(), "data", "usage_data.json")
        success = self._save_json_file(usage_data_path, usage_data)
        if success:
            print(f"  Saved usage data to: {usage_data_path}")
        return success

    # This method is now handled by _load_json_file with create_if_missing=True
    def create_default_usage_data(self):
        """Creates a default usage data file if it doesn't exist."""
        usage_data_path = os.path.join(os.getcwd(), "data", "usage_data.json")
        return self._save_json_file(usage_data_path, {})