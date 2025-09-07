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
        self.is_known = is_known # Indicates if the tag is loaded from CSV (known) or from the .txt file for the image. 
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
        # Search index for quick lookups
        self.search_index = {}  # Maps lowercase tag name segments to lists of TagData objects
        self.tags_by_name = {}  # Maps tag name to TagData for O(1) lookups

    def load_tags_from_csv(self, csv_path):
        """Loads tags from the specified CSV file."""
        import csv
        import time
        
        start_time = time.time()
        print(f"Loading tags from CSV: {csv_path}")
        
        try:
            # Create a set of existing tag names for faster duplicate checking
            existing_tag_names = set()
            
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                # Preallocate list capacity for better performance
                tags_to_add = []
                
                for row in reader:
                    # Extract data from CSV, handling potential errors
                    try:
                        name = row['name']
                        category = row['category']
                        post_count = int(row['post_count'])  # Convert to integer
                    except (KeyError, ValueError) as e:
                        print(f"Skipping row due to error: {e} - Row data: {row}")
                        continue  # Skip to the next row

                    # Check for duplicates by name using set (O(1) lookup)
                    if name in existing_tag_names:
                        print(f"Duplicate tag found: {name}, skipping.")
                        continue
                    
                    existing_tag_names.add(name)
                    tag_data = TagData(name=name, category=category, post_count=post_count)
                    tags_to_add.append(tag_data)
                
                # Extend the list at once instead of appending one by one
                self.tags.extend(tags_to_add)
                
                # Build the search index
                self._build_search_index()

            end_time = time.time()
            print(f"Loaded {len(self.tags)} tags from CSV in {end_time - start_time:.4f} seconds.")
        except FileNotFoundError:
            print(f"Error: CSV file not found at {csv_path}")
        except Exception as e:
            print(f"Error loading tags from CSV: {e}")
            
    def _build_search_index(self):
        """Builds the search index for faster tag lookup."""
        import time
        
        start_time = time.time()
        print("Building search index...")
        
        # Clear existing indexes
        self.search_index = {}
        self.tags_by_name = {}
        
        for tag_data in self.tags:
            if not tag_data.is_known:
                continue  # Skip unknown tags in the index
                
            # Add to tags_by_name dictionary for O(1) lookups
            self.tags_by_name[tag_data.name] = tag_data
            
            # Add to search index
            tag_name_spaces = FileOperations.convert_underscores_to_spaces(tag_data.name.lower())
            
            # Index the full tag name
            if tag_name_spaces not in self.search_index:
                self.search_index[tag_name_spaces] = []
            self.search_index[tag_name_spaces].append(tag_data)
            
            # Index each word separately for better substring matching
            words = tag_name_spaces.split()
            for word in words:
                if word not in self.search_index:
                    self.search_index[word] = []
                if tag_data not in self.search_index[word]:
                    self.search_index[word].append(tag_data)
                    
        end_time = time.time()
        print(f"Search index built in {end_time - start_time:.4f} seconds. Indexed {len(self.search_index)} terms.")
    
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
        """Adds a tag and updates the search index if it's a known tag"""
        self.tags.append(tag_data)
        
        # Update tags_by_name dictionary
        self.tags_by_name[tag_data.name] = tag_data
        
        # Only add known tags to the search index
        if tag_data.is_known:
            # Add to search index
            tag_name_spaces = FileOperations.convert_underscores_to_spaces(tag_data.name.lower())
            
            # Index the full tag name
            if tag_name_spaces not in self.search_index:
                self.search_index[tag_name_spaces] = []
            self.search_index[tag_name_spaces].append(tag_data)
            
            # Index each word separately
            words = tag_name_spaces.split()
            for word in words:
                if word not in self.search_index:
                    self.search_index[word] = []
                if tag_data not in self.search_index[word]:
                    self.search_index[word].append(tag_data)

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
            self.tags_selected_changed.emit()  # Keep existing signal for backward compatibility TODO: is anything broken if this is removed? check search panel

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
        Searches for tags based on the query using the optimized search index.
        Returns an empty list for empty queries.
        Orders results by post_count (descending).
        Limits results to MAX_SEARCH_RESULTS.
        """
        import time
        
        # TODO: Make this a configurable setting in the UI once we add user configuration menus
        MAX_SEARCH_RESULTS = 50  # Limit search results to 50 items for better performance
        
        start_time = time.time()
        
        if not query: # Check if the query is empty
            return [] # Return empty list if query is empty
            
        query_spaces = FileOperations.convert_underscores_to_spaces(query.lower())
        result_set = set()  # Use a set to avoid duplicates
            
        if exact_match:
            # For exact match, we need to find tags where the ENTIRE name equals our query
            # We can't just use the index directly, as it might match partial words
            for tag_data in self.get_known_tags():
                # Convert tag name to space format just like the query
                tag_name_spaces = FileOperations.convert_underscores_to_spaces(tag_data.name.lower())
                if tag_name_spaces == query_spaces:  # Exact equality check
                    result_set.add(tag_data)
        else:
            # Fuzzy match - find all tags that contain the query
            # Check each key in the search index that contains our query
            matching_keys = [key for key in self.search_index.keys() if query_spaces in key]
            
            # If the query is a single letter or short string, this could return too many results
            # For very short queries, we can optimize by doing a more targeted search
            if len(query_spaces) <= 2:
                # For short queries, limit to keys that start with the query
                matching_keys = [key for key in matching_keys if key.startswith(query_spaces)]
            
            # Add all tags from matching keys to our result set
            for key in matching_keys:
                result_set.update(self.search_index[key])
                
            # If we still have too many results, we can limit further
            if len(result_set) > 1000:
                # Convert to list for sorting
                result_list = list(result_set)
                # Sort by post_count and take top 1000
                result_list.sort(key=attrgetter('post_count'), reverse=True)
                result_set = set(result_list[:1000])
            
        # Convert set back to list for final sorting
        filtered_tags = list(result_set)
        filtered_tags.sort(key=attrgetter('post_count'), reverse=True)
        
        # Limit to MAX_SEARCH_RESULTS
        total_matches = len(filtered_tags)
        filtered_tags = filtered_tags[:MAX_SEARCH_RESULTS]
        
        end_time = time.time()
        print(f"Search for '{query}' took {end_time - start_time:.4f} seconds with {total_matches} matches (showing {len(filtered_tags)})")
        
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