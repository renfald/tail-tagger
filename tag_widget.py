from PySide6.QtWidgets import QLabel, QFrame, QSizePolicy, QHBoxLayout
from PySide6.QtCore import Qt, QSize, Signal, QMimeData, QPoint
from PySide6.QtGui import QDrag, QFont, QPixmap, QContextMenuEvent
from math import sqrt
from file_operations import FileOperations
from theme import TAG_CATEGORY_COLORS
class TagWidget(QFrame):
    """Widget to display a tag."""

    tag_clicked = Signal(str)
    favorite_star_clicked = Signal(str)
    tag_right_clicked = Signal(str)

    def __init__(self, tag_data, is_selected=None, is_known_tag=None):
        """Initializes a TagWidget.

        Args:
            tag_data (TagData): The TagData object representing the tag. # Modified docstring
            is_selected (bool, optional): Whether the tag is selected. Defaults to False. # Keep for now, panel can override if needed
            is_known_tag (bool, optional): Whether the tag is "known". Defaults to True. # Keep for now, panel can override if needed
        """
        super().__init__()
        self.tag_data = tag_data # Store TagData object
        self.tag_name = tag_data.name # Extract tag_name from TagData
        self.is_selected = is_selected if is_selected is not None else tag_data.selected # Use constructor param if provided, else TagData
        self.is_known_tag = is_known_tag if is_known_tag is not None else tag_data.is_known # Use constructor param if provided, else TagData
        self.styling_mode = "dim_on_select"
        self._setup_ui()
        self._update_style()
        
        # Initialize with elided text
        # Need to use a short timer because widget sizes aren't properly initialized yet
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, self._update_elided_text)
        
        # Register as an observer for this tag's data changes
        self.tag_data.add_observer(self._on_tag_data_changed)

        self._is_cleaned_up = False

    def cleanup(self):
        """Properly disconnect signals and remove observers before widget deletion."""
        if self._is_cleaned_up:
            return
        self._is_cleaned_up = True

        try:
            self.tag_clicked.disconnect()
        except RuntimeError:
            pass
        except Exception as e:
            print(f"Unexpected error disconnecting tag_clicked for '{self.tag_name}': {e}")

        try:
            self.favorite_star_clicked.disconnect()
        except RuntimeError:
            pass
        except Exception as e:
            print(f"Unexpected error disconnecting favorite_star_clicked for '{self.tag_name}': {e}")

        try:
            self.tag_right_clicked.disconnect()
        except RuntimeError:
            pass
        except Exception as e:
            print(f"Unexpected error disconnecting tag_right_clicked for '{self.tag_name}': {e}")

        if hasattr(self, 'tag_data') and self.tag_data:
            try:
                self.tag_data.remove_observer(self._on_tag_data_changed)
            except (RuntimeError, ValueError):
                pass
            except Exception as e:
                print(f"Unexpected error removing observer for '{self.tag_name}': {e}")

    def set_is_known_tag(self, is_known_tag):
        """Sets the is_known_tag property."""
        self.is_known_tag = is_known_tag
        self._update_style()

    def _setup_ui(self):
        """Sets up the UI elements."""
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        tag_layout = QHBoxLayout()
        tag_layout.setContentsMargins(0, 0, 0, 0) # Removing any default margins and letting the label control it
        tag_layout.setSpacing(0) # Removing any default spacing

        

        self.tag_label = QLabel(FileOperations.convert_underscores_to_spaces(self.tag_name)) # Tag name with underscores replaced by spaces
        self.tag_label.setAlignment(Qt.AlignCenter)
        self.tag_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.tag_label.setContentsMargins(3, 3, 3, 3) # The widget will shrink to 6 pixels larger than the text before scrolling
        
        # Enable text eliding with ellipsis for long text
        self.tag_label.setTextFormat(Qt.PlainText)
        self.tag_label.setWordWrap(False)
        # Maximum width will be set in resizeEvent
        
        # --- Star Icon Label ---
        self.star_label = QLabel(self)  # Create QLabel instance
        self.star_label.setFixedSize(QSize(22, 22)) # Set a fixed size for the star icon (adjust as needed)
        self.star_label.setScaledContents(True) # Ensure SVG scales nicely to fit label size
        self.star_label.hide() # Initially hide the star icon
        # --- End Star Icon Label ---

        # --- Set Initial Star Icon ---
        from PySide6.QtGui import QPixmap # Import QPixmap here
        pixmap = QPixmap(":/icons/star-outline.svg") # Load the outline star SVG from resources
        self.star_label.setPixmap(pixmap) # Set the pixmap for the star_label
        # --- End Set Initial Star Icon ---

        tag_layout.addWidget(self.tag_label)
        tag_layout.addWidget(self.star_label)
        self.setLayout(tag_layout)


    def mousePressEvent(self, event):
        """Handles mouse press events to initiate drag detection."""
        super().mousePressEvent(event) # Call base class implementation first! Important for focus and other default behaviors.
        if event.button() == Qt.LeftButton:
            self.start_drag_pos = event.pos()  # Record starting position
            self.start_drag_global_pos = event.globalPos() # Needed for calculating global distance
            print(f"Mouse press event. tag: {self.tag_name}, pos: {self.start_drag_pos}, global: {self.start_drag_global_pos}") # Debug

    def mouseMoveEvent(self, event):
        """Handles mouse move events to initiate drag operation."""
        print(f"mouseMoveEvent called for tag: {self.tag_name}") # Debug

        if event.buttons() != Qt.LeftButton: # Check if left button is still pressed
            print(f"mouseMoveEvent: Ignoring because left button is not pressed.") #Debug
            return # Ignore if not left button drag

        dx = event.globalPos().x() - self.start_drag_global_pos.x() # Calculate horizontal movement
        dy = event.globalPos().y() - self.start_drag_global_pos.y() # Calculate vertical movement
        distance = sqrt(dx * dx + dy * dy) # Calculate total distance using hypotenuse

        print(f"mouseMoveEvent: tag={self.tag_name}, distance={distance:.2f}") # Debug

        # Get the parent panel to check if the tag is draggable
        parent_panel = self.parent()
        while parent_panel and not hasattr(parent_panel, 'is_tag_draggable'):
            parent_panel = parent_panel.parent()
        
        # Check if tag is draggable
        is_draggable = False
        if parent_panel and hasattr(parent_panel, 'is_tag_draggable'):
            is_draggable = parent_panel.is_tag_draggable(self.tag_name)
            print(f"Tag '{self.tag_name}' draggable: {is_draggable}")
        
        if distance > 8: # Drag threshold (pixels) - Always initiate a drag to allow "escape" from misclicks
            print(f"Initiating drag for tag: {self.tag_name}") # Debug
            drag = QDrag(self) # Create QDrag object, passing self (TagWidget) as parent
            mime_data = QMimeData() # Create QMimeData object to hold drag data
            mime_data.setText(self.tag_name) # For now, just tag name as plain text
            drag.setMimeData(mime_data) # Set the mime data for the drag operation

            if is_draggable:
                # --- For draggable tags: Full drag visual experience ---
                # Create a semi-transparent pixmap for drag representation
                original_pixmap = self.grab() # Grab a pixmap of the TagWidget
                pixmap = QPixmap(original_pixmap.size()) # Create a new QPixmap of the same size
                pixmap.fill(Qt.transparent) # Fill the new pixmap with transparency

                from PySide6.QtGui import QPainter, QColor # Ensure QColor is imported
                painter = QPainter(pixmap) # Create a QPainter to draw on the new pixmap
                painter.setOpacity(0.5) # Set the opacity for the painter (0.0 - 1.0) - Adjust as needed!
                painter.drawPixmap(pixmap.rect(), original_pixmap) # Draw the original pixmap onto the new one with opacity
                painter.end() # End painting

                drag.setPixmap(pixmap) # Set the semi-transparent pixmap
     
                hot_spot_x = pixmap.width() // 2  # Center X-coordinate of the pixmap
                hot_spot_y = pixmap.height() // 2 # Top Y-coordinate (we want to align top edge vertically)
                drag.setHotSpot(QPoint(hot_spot_x, hot_spot_y)) # Set the hotspot

                self.hide() # Hide the TagWidget itself during drag
            else:
                # --- For non-draggable tags: "Empty" drag with no visuals ---
                # Create a 1x1 transparent pixmap (effectively invisible)
                empty_pixmap = QPixmap(1, 1)
                empty_pixmap.fill(Qt.transparent)
                drag.setPixmap(empty_pixmap)
                # Don't hide the tag for non-draggable panels
            
            drop_action = drag.exec(Qt.MoveAction)
            
            if is_draggable:
                if drop_action == Qt.MoveAction:
                    print(f"Drag successful for tag: {self.tag_name}. MoveAction returned.") # Debug - successful drop
                    # Drop was handled by a target, no need to show tag again here.
                else:
                    print(f"Drag cancelled/invalid for tag: {self.tag_name}. Action: {drop_action}") # Debug - cancelled/invalid drop
                    self.show()
            
            print(f"Drag operation completed for tag: {self.tag_name}") # Debug

    def mouseReleaseEvent(self, event):
        """Handles mouse release events."""
        print(f"TagWidget '{self.tag_name}' mouseReleaseEvent!")
        if event.button() == Qt.LeftButton:  # Only handle left clicks
            if self.star_label.geometry().contains(event.pos()): # Check if click is within star_label
                print(f"Star icon clicked for tag: {self.tag_name}") # Debug
                self.favorite_star_clicked.emit(self.tag_name) # Emit favorite_star_clicked signal
            else:
                print(f"Tag label clicked for tag: {self.tag_name}") # Debug
                self.tag_clicked.emit(self.tag_name)  # Emit the tag_clicked signal (existing functionality)
        super().mouseReleaseEvent(event) # keep default functionality just in case

    def _update_style(self):
        """Updates the visual style."""
        # Get category color, defaulting to '9' (unknown) if category is not found
        category_color = TAG_CATEGORY_COLORS.get(self.tag_data.category, TAG_CATEGORY_COLORS["9"])

        # --- Base Styles (Apply to all states) ---
        # Apply border-radius to all corners of the tag_label
        base_style = f"""
            background-color: #353535;
            color: white;
            border: 1px solid #121212;
            border-radius: 5px;
        """
        
        # --- Font Settings (Apply to all states) ---
        font = QFont()
        font.setPointSize(8)
        self.tag_label.setFont(font)
        
        # --- State-Specific Styles ---
        if not self.is_known_tag:
            # Unknown Tag Style: overrides background and text color, and uses 'invalid' stripe color
            style = base_style + "background-color: #552121; color: #855252;"
            # For unknown tags, the left border is always the invalid color
            style += f"border-left: 2px solid {TAG_CATEGORY_COLORS['6']};"
        elif self.styling_mode == "dim_on_select" and self.is_selected:
            # Selected (Dimmed) Style: overrides background and text color
            style = base_style + "background-color: #242424; color: #888888;"
            # Apply category color to left border for dimmed tags
            style += f"border-left: 2px solid {category_color};"
        else:
            # Default (Known, Unselected) Style: uses base_style
            style = base_style  # No additional changes needed
            # Apply category color to left border for normal tags
            style += f"border-left: 2px solid {category_color};"

        # --- Apply the Combined Stylesheet to label ---
        self.tag_label.setStyleSheet(style)
        # Setting a separate stylesheet for the widget itself to set tooltip colors. Baindaid because I did a bad job setting overall styling in this app
        self.setStyleSheet("QToolTip { color: #FFFFFF; background-color: #353535; border: 1px solid #555555; }")


    def set_selected(self, is_selected):
        """Sets the selection state."""
        self.is_selected = is_selected
        self._update_style()

    def set_styling_mode(self, mode):
        """Sets the styling mode for the TagWidget."""
        if mode in ["dim_on_select", "ignore_select"]:
            self.styling_mode = mode
            self._update_style()  # Re-apply style
        else:
            print(f"Warning: Invalid styling mode: {mode}")

    # --- Hover Event Handlers ---
    def enterEvent(self, event):
        """Handles mouse enter events."""
        # print(f"Mouse enter event for tag: {self.tag_name}") # Debug
        self.set_favorite_state() # Call set_favorite_state on hover

    def leaveEvent(self, event):
        """Handles mouse leave events."""
        # print(f"Mouse leave event for tag: {self.tag_name}") # Debug
        self.set_favorite_state() # Call set_favorite_state on leave
    # --- End Hover Event Handlers ---

        # --- set_favorite_state method (Implementation in next action) ---
    def set_favorite_state(self):
        """Updates the star icon based on favorite state and hover."""
        from PySide6.QtGui import QPixmap # Import QPixmap here (if not already imported)

        # Determine star icon based on tag_data.favorite (currently always False)
        if self.tag_data.favorite: # Access tag_data.favorite directly! (Currently always False)
            pixmap = QPixmap(":/icons/star-fill.svg")
        else:
            pixmap = QPixmap(":/icons/star-outline.svg")

        # Store current visibility state
        was_visible = self.star_label.isVisible()
        
        # Show star ONLY on hover AND if it's a known tag
        should_be_visible = self.underMouse() and self.is_known_tag
        
        # Update visibility and pixmap when needed
        if should_be_visible:
            self.star_label.setPixmap(pixmap) # Set the appropriate star icon
            self.star_label.show() # Show the star label
        else:
            self.star_label.hide() # Hide the star label
            
        # If visibility changed, update the elided text
        if was_visible != should_be_visible:
            self._update_elided_text()

    def contextMenuEvent(self, event: QContextMenuEvent):
        """Handles right-click context menu events for the TagWidget."""
        if event.reason() == QContextMenuEvent.Mouse:
            print(f"Right-click detected on tag: {self.tag_name}")
            self.tag_right_clicked.emit(self.tag_name)
            event.accept()
        else:
            super().contextMenuEvent(event) # Call base class implementation for non-mouse context menus
            
    def _on_tag_data_changed(self):
        """Called when this tag's data changes."""
        if self._is_cleaned_up:
            return

        self.is_selected = self.tag_data.selected
        self.is_known_tag = self.tag_data.is_known
        self._update_style()
        self._update_elided_text()
            
    def hideEvent(self, event):
        """Handle widget being hidden."""
        super().hideEvent(event)
        
    def closeEvent(self, event):
        """Handle widget being closed."""
        self.cleanup()
        super().closeEvent(event)
        
    def resizeEvent(self, event):
        """Handle widget resize events to adjust text eliding."""
        super().resizeEvent(event)
        self._update_elided_text()
        
    def _update_elided_text(self):
        """Update the label text with elision based on available width."""
        if self._is_cleaned_up:
            return

        from PySide6.QtGui import QFontMetrics
        
        # Get original text (with spaces instead of underscores)
        original_text = FileOperations.convert_underscores_to_spaces(self.tag_name)
        
        # Get the parent container width (scroll area viewport)
        parent_width = 0
        parent = self.parent()
        
        # Look for an appropriate parent to determine max width
        if parent:
            # Try to find parent scroll area viewport
            while parent and not parent.inherits("QScrollArea") and not parent.inherits("QViewport"):
                parent = parent.parent()
                
            if parent:
                if parent.inherits("QScrollArea"):
                    # If we found a scroll area, use its viewport width
                    parent_width = parent.viewport().width()
                else:
                    # Otherwise use the parent width directly
                    parent_width = parent.width()
            
            # If we couldn't find a suitable parent, use tag widget width
            if parent_width <= 0:
                parent_width = self.width()
        else:
            # Fallback if no parent
            parent_width = self.width()
        
        # Account for container layout margins and spacing
        parent_width -= 1  # Safe buffer for container margins/spacing
        
        # Calculate available width for text within this tag widget
        available_width = parent_width
        
        # For known tags, account for star icon space whether visible or not
        # For unknown tags, the star will never be visible so we can use the full width
        if self.is_known_tag:
            # Account for star icon width to prevent text jumping when star appears/disappears
            available_width -= self.star_label.width()
            
        # Account for label margins
        available_width -= (self.tag_label.contentsMargins().left() + self.tag_label.contentsMargins().right())
        
        # Apply a small buffer to ensure text doesn't touch edges
        available_width -= 1
        
        # If there's not enough width, elide the text
        if available_width > 10:  # Ensure minimum sensible width
            font_metrics = QFontMetrics(self.tag_label.font())
            elided_text = font_metrics.elidedText(original_text, Qt.ElideRight, available_width)
            self.tag_label.setText(elided_text)
        else:
            # Fallback if available width calculation is invalid
            self.tag_label.setText(original_text)