from PySide6.QtCore import QAbstractListModel, Qt, QModelIndex, Signal
from operator import attrgetter
from file_operations import FileOperations

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

                    # Check for duplicates by name
                    if any(tag.name == name for tag in self.tags):
                        print(f"Duplicate tag found: {name}, skipping.")
                        continue

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

    def get_favorite_tags(self):
        """Returns all tags."""
        return [tag for tag in self.tags if tag.favorite]

    def add_tag(self, tag_data):
        """Adds a tag"""
        self.tags.append(tag_data)

    def remove_tag(self, tag_data_to_remove):
        """Removes a specific TagData object from the tag list."""
        if tag_data_to_remove in self.tags:
            self.beginResetModel() # Or beginRemoveRows/endRemoveRows for more specific signal
            self.tags.remove(tag_data_to_remove)
            self.endResetModel() # Or endRemoveRows
            self.tags_selected_changed.emit() # Notify panels of change
            print(f"Tag '{tag_data_to_remove.name}' removed from TagListModel.")
        else:
            print(f"Warning: Tag '{tag_data_to_remove.name}' not found in TagListModel for removal.")
    
    def clear_tags(self):
        """Clears all tags."""
        self.tags = []
    
    def set_tag_selected_state(self, tag_name, is_tag_selected):
        """Set the current selection state for a given tag."""
        tag = next((tag for tag in self.tags if tag.name == tag_name), None)
        if tag:
            tag.selected = is_tag_selected
            self.tags_selected_changed.emit()

    def remove_unknown_tags(self):
        """Removes any tags where is_known is False from the tag list."""
        self.tags = [tag for tag in self.tags if tag.is_known]

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

    def get_known_tags(self):
        """Returns a list of all known tags."""
        return [tag for tag in self.tags if tag.is_known]

    def search_tags(self, query):
        """
        Performs a basic substring search for tags.
        Handles empty queries by returning an empty list.
        Orders search results by frequency (descending).
        Implements underscore/space agnostic search.
        Returns a list of TagData objects whose names contain the query (case-insensitive), ordered by frequency.
        """
        if not query: # Check if the query is empty
            return [] # Return empty list if query is empty

        query_spaces = FileOperations.convert_underscores_to_spaces(query.lower()) # Convert query to space-separated lowercase
        filtered_tags = []
        for tag_data in self.get_known_tags(): # Search within known tags only
            tag_name_spaces = FileOperations.convert_underscores_to_spaces(tag_data.name.lower()) # Convert tag name to space-separated lowercase
            if query_spaces in tag_name_spaces: # Case-insensitive substring check on space-separated names
                filtered_tags.append(tag_data)

        filtered_tags.sort(key=attrgetter('frequency'), reverse=True)
        return filtered_tags