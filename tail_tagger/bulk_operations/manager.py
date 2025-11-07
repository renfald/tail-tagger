import os
import json
import shutil
from datetime import datetime


class BulkOperationsManager:
    """Manages bulk tag operations across all images in a folder.

    This manager handles operations that modify tags across multiple images at once,
    bypassing the normal image-by-image flow for performance reasons.
    """

    def __init__(self, file_operations):
        """Initialize the bulk operations manager.

        Args:
            file_operations (FileOperations): Instance of FileOperations for file I/O
        """
        self.file_operations = file_operations

    def add_tag_to_all(self, folder_path, tag_name, position='end', progress_callback=None):
        """Adds a tag to all images in the folder.

        If the tag already exists on an image, it will be moved to the specified position.

        Args:
            folder_path (str): Path to the image folder
            tag_name (str): Name of the tag to add
            position (str): 'front' or 'end' - where to place the tag
            progress_callback (callable, optional): Callback function(phase, current, total, message)
                where phase is 'init' or 'process'

        Returns:
            dict: Results with keys:
                - 'success': bool
                - 'added_count': number of images where tag was added
                - 'moved_count': number of images where tag was moved
                - 'total_images': total images processed
                - 'error': error message if success is False
        """
        try:
            # Phase 1: Ensure workfile is complete
            if progress_callback:
                progress_callback('init', 0, 0, 'Initializing workfile...')

            workfile_data, initialized = self.file_operations.ensure_workfile_complete(
                folder_path,
                progress_callback=lambda cur, total: progress_callback('init', cur, total, f'Loading image data... ({cur}/{total})') if progress_callback else None
            )

            if not workfile_data.get("image_tags"):
                return {
                    'success': False,
                    'added_count': 0,
                    'moved_count': 0,
                    'total_images': 0,
                    'error': 'No images found in folder'
                }

            # Phase 2: Add/move tag in all images
            total_images = len(workfile_data["image_tags"])
            added_count = 0
            moved_count = 0

            for index, (image_path, tags) in enumerate(workfile_data["image_tags"].items()):
                if progress_callback:
                    progress_callback('process', index + 1, total_images, f'Processing images... ({index + 1}/{total_images})')

                # Check if tag already exists
                if tag_name in tags:
                    # Remove it so we can move it to the correct position
                    tags.remove(tag_name)
                    moved_count += 1
                else:
                    added_count += 1

                # Add tag at specified position
                if position == 'front':
                    tags.insert(0, tag_name)
                else:  # 'end'
                    tags.append(tag_name)

            # Phase 3: Save workfile with backup
            if progress_callback:
                progress_callback('process', total_images, total_images, 'Saving changes...')

            self._save_workfile_with_backup(folder_path, workfile_data)

            return {
                'success': True,
                'added_count': added_count,
                'moved_count': moved_count,
                'total_images': total_images,
                'error': None
            }

        except Exception as e:
            return {
                'success': False,
                'added_count': 0,
                'moved_count': 0,
                'total_images': 0,
                'error': str(e)
            }

    def remove_tag_from_all(self, folder_path, tag_name, progress_callback=None):
        """Removes a tag from all images in the folder.

        Args:
            folder_path (str): Path to the image folder
            tag_name (str): Name of the tag to remove
            progress_callback (callable, optional): Callback function(phase, current, total, message)
                where phase is 'init' or 'process'

        Returns:
            dict: Results with keys:
                - 'success': bool
                - 'removed_count': number of images where tag was removed
                - 'total_images': total images processed
                - 'error': error message if success is False
        """
        try:
            # Phase 1: Ensure workfile is complete
            if progress_callback:
                progress_callback('init', 0, 0, 'Initializing workfile...')

            workfile_data, initialized = self.file_operations.ensure_workfile_complete(
                folder_path,
                progress_callback=lambda cur, total: progress_callback('init', cur, total, f'Loading image data... ({cur}/{total})') if progress_callback else None
            )

            if not workfile_data.get("image_tags"):
                return {
                    'success': False,
                    'removed_count': 0,
                    'total_images': 0,
                    'error': 'No images found in folder'
                }

            # Phase 2: Remove tag from all images
            total_images = len(workfile_data["image_tags"])
            removed_count = 0

            for index, (image_path, tags) in enumerate(workfile_data["image_tags"].items()):
                if progress_callback:
                    progress_callback('process', index + 1, total_images, f'Processing images... ({index + 1}/{total_images})')

                # Remove tag if present
                if tag_name in tags:
                    tags.remove(tag_name)
                    removed_count += 1

            # Phase 3: Save workfile with backup
            if progress_callback:
                progress_callback('process', total_images, total_images, 'Saving changes...')

            self._save_workfile_with_backup(folder_path, workfile_data)

            return {
                'success': True,
                'removed_count': removed_count,
                'total_images': total_images,
                'error': None
            }

        except Exception as e:
            return {
                'success': False,
                'removed_count': 0,
                'total_images': 0,
                'error': str(e)
            }

    def _save_workfile_with_backup(self, folder_path, workfile_data):
        """Saves workfile with a timestamped backup.

        Args:
            folder_path (str): Path to the image folder
            workfile_data (dict): Workfile data to save

        Raises:
            Exception: If saving fails
        """
        workfile_path = self.file_operations.get_workfile_path(folder_path)

        # Create backup if workfile exists
        if os.path.exists(workfile_path):
            # Create backups subfolder in staging directory
            staging_folder = os.path.dirname(workfile_path)
            backups_folder = os.path.join(staging_folder, 'backups')
            os.makedirs(backups_folder, exist_ok=True)

            # Generate backup filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            workfile_filename = os.path.basename(workfile_path)
            backup_filename = workfile_filename.replace('.json', f'_backup_{timestamp}.json')
            backup_path = os.path.join(backups_folder, backup_filename)

            try:
                shutil.copy2(workfile_path, backup_path)
                print(f"Created backup: {backup_path}")
            except Exception as e:
                print(f"Warning: Could not create backup: {e}")

        # Save workfile
        try:
            with open(workfile_path, 'w', encoding='utf-8') as f:
                json.dump(workfile_data, f, indent=2)
            print(f"Saved workfile: {workfile_path}")
        except Exception as e:
            print(f"Error saving workfile: {e}")
            raise
