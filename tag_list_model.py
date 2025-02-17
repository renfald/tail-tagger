from PySide6.QtCore import QAbstractListModel, Qt, QModelIndex, Signal

class TagData:
    def __init__(self, name, category=None, frequency=None, selected=False, favorite=False, is_known=True):
        self.name = name
        self.category = category
        self.frequency = frequency
        self.selected = selected
        self.favorite = favorite
        self.is_known = is_known


class TagListModel(QAbstractListModel):
    """A model to hold a list of tags."""

    tags_selected_changed = Signal() # Add Signal

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tags = []

    def load_tags_from_csv(self, csv_path):
        """Loads tags from the specified CSV file."""
        import csv
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Extract data from CSV, handling potential errors
                    try:
                        name = row['name']
                        category = row['category']
                        frequency = int(row['post_count'])  # Convert to integer
                    except (KeyError, ValueError) as e:
                        print(f"Skipping row due to error: {e} - Row data: {row}")
                        continue  # Skip to the next row

                    tag_data = TagData(name=name, category=category, frequency=frequency)
                    self.tags.append(tag_data)
            print(f"Loaded {len(self.tags)} tags from CSV.")
        except FileNotFoundError:
            print(f"Error: CSV file not found at {csv_path}")
        except Exception as e:
            print(f"Error loading tags from CSV: {e}")

    def get_all_tags(self):
        """Returns all tags."""
        return self.tags

    def add_tag(self, tag_data):
        """Adds a tag"""
        self.tags.append(tag_data)

    def clear_tags(self):
        """Clears all tags."""
        self.tags = []
    
    def set_tag_selected(self, tag_name, selected):
        """Sets tag to selected"""
        for tag in self.tags:
            if tag.name == tag_name:
                tag.selected = selected
        self.tags_selected_changed.emit()

    def remove_unknown_tags(self):
        """Removes any tags where is_known is False from the tag list."""
        self.tags = [tag for tag in self.tags if tag.is_known]
        self.tags_selected_changed.emit()   # not sure if this is the proper name for the event. may change it later

    def rowCount(self, parent=QModelIndex()):
        """Returns the number of rows (tags)."""
        return len(self.tags) # Modified

    def data(self, index, role=Qt.DisplayRole):
        """Returns data for a specific item and role."""
        return None # Modified
    
    def clear_selected_tags(self):
        """Resets the 'selected' status of all tags to False."""
        for tag in self.tags:
            tag.selected = False
        self.tags_selected_changed.emit() # Notify any listeners