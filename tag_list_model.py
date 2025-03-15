from PySide6.QtCore import QAbstractListModel, Qt, QModelIndex, Signal
from operator import attrgetter
from file_operations import FileOperations
from heapq import nlargest

class TagData:
    def __init__(self, name, category=None, post_count=None, selected=False, favorite=False, is_known=True):
        self.name = name
        self.category = category
        self.post_count = post_count
        self.selected = selected
        self.favorite = favorite
        self.is_known = is_known
        self.observers = []  # List of functions to call when this tag's state changes
    
    def add_observer(self, callback):
        """Add a callback function to be notified when this tag's state changes."""
        if callback not in self.observers:
            self.observers.append(callback)
    
    def remove_observer(self, callback):
        """Remove a callback function from the observers list."""
        if callback in self.observers:
            self.observers.remove(callback)
    
    def notify_observers(self):
        """Notify all observers that this tag's state has changed."""
        # Make a copy of the observers list to avoid issues if observers 
        # remove themselves during notification
        observers_copy = self.observers.copy()
        for callback in observers_copy:
            try:
                callback()
            except RuntimeError as e:
                # If we hit a deleted Qt object, remove it from observers
                print(f"Observer error for tag {self.name}: {e}")
                if callback in self.observers:
                    self.observers.remove(callback)


class TagListModel(QAbstractListModel):
    """A model to hold a list of tags."""

    tags_selected_changed = Signal() # Add Signal
    tag_state_changed = Signal(str)  # Signal emitted when a specific tag's state changes

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tags = []
        self.tag_usage_counts = self._load_usage_data()

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
                        post_count = int(row['post_count'])  # Convert to integer
                    except (KeyError, ValueError) as e:
                        print(f"Skipping row due to error: {e} - Row data: {row}")
                        continue  # Skip to the next row

                    # Check for duplicates by name
                    if any(tag.name == name for tag in self.tags):
                        print(f"Duplicate tag found: {name}, skipping.")
                        continue

                    tag_data = TagData(name=name, category=category, post_count=post_count)
                    self.tags.append(tag_data)

            print(f"Loaded {len(self.tags)} tags from CSV.")
        except FileNotFoundError:
            print(f"Error: CSV file not found at {csv_path}")
        except Exception as e:
            print(f"Error loading tags from CSV: {e}")
    
    def _load_usage_data(self):
        """Loads usage data using FileOperations."""
        file_operations = FileOperations() # Create FileOperations instance
        return file_operations.load_usage_data() # Call load_usage_data and return the dictionary
    
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
            tag.notify_observers()  # Notify observers of this specific tag
            self.tag_state_changed.emit(tag_name)  # Emit signal with tag name
            self.tags_selected_changed.emit()  # Keep existing signal for backward compatibility

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

    def search_tags(self, query, exact_match):
        """
        Searches for tags based on the query.
        Returns an empty list for empty queries.
        Orders results by post_count (descending).
        """
        if not query: # Check if the query is empty
            return [] # Return empty list if query is empty

        query_spaces = FileOperations.convert_underscores_to_spaces(query.lower()) # Convert query to space-separated lowercase
        filtered_tags = []
        for tag_data in self.get_known_tags(): # Search within known tags only
            tag_name_spaces = FileOperations.convert_underscores_to_spaces(tag_data.name.lower()) # Convert tag name to space-separated lowercase
        
            if exact_match:
                # --- Exact Match Logic ---
                if query_spaces == tag_name_spaces: # Exact equality check for Exact Match
                    filtered_tags.append(tag_data) 
            else:
                # --- Fuzzy Match Logic (Existing Substring Search) ---
                if query_spaces in tag_name_spaces: # Case-insensitive substring check on space-separated names
                    filtered_tags.append(tag_data)

        filtered_tags.sort(key=attrgetter('post_count'), reverse=True)
        return filtered_tags
    
    def increment_tag_usage(self, tag_name):
        """Increments the usage count for a given tag name."""
        underscored_tag_name = FileOperations.convert_spaces_to_underscores(tag_name) # Convert to underscore format for consistency
        if underscored_tag_name in self.tag_usage_counts:
            self.tag_usage_counts[underscored_tag_name] += 1 # Increment existing count
        else:
            self.tag_usage_counts[underscored_tag_name] = 1 # Initialize count to 1 if tag is new to usage data
        print(f"  Tag usage count incremented for '{underscored_tag_name}': {self.tag_usage_counts[underscored_tag_name]}") # Debug message

    def get_frequent_tags(self, top_n=30):
        """
        Returns the top `top_n` most frequently used tags, ordered by usage count, then post_count, then name.
        """
        # Step 1: Build a list of (primary, secondary, tertiary, TagData) tuples
        frequent_tag_tuples = [
            (self.tag_usage_counts.get(tag.name, 0),  # Usage count (primary sort key)
            tag.post_count,                             # post_count (secondary tie-breaker)
            tag.name,                                    # Tag name (tertiary tie-breaker)
            tag)                                         # TagData object
            for tag in self.get_known_tags() # <--- Filter for known tags here
            if tag.name in self.tag_usage_counts # <--- Ensure tag has usage data
        ]

        # Step 2: Get the top `top_n` using heapq.nlargest()
        top_tags = [tag for _, _, _, tag in nlargest(top_n, frequent_tag_tuples)]

        return top_tags
   
    def remove_tag_usage(self, tag_name):
        """Removes the usage data for a given tag name."""
        underscored_tag_name = FileOperations.convert_spaces_to_underscores(tag_name) # Convert to underscore format for consistency
        if underscored_tag_name in self.tag_usage_counts:
            del self.tag_usage_counts[underscored_tag_name] # Remove tag from usage_counts dict
            print(f"  Usage data removed for tag: '{underscored_tag_name}'") # Debug message
        else:
            print(f"  Warning: No usage data found for tag '{underscored_tag_name}' to remove.") # Warning if no data found