"""Keep a screen's contents inside the terminal, however short it is.

Textual sizes these boxes from their contents, so on a short terminal the
bottom of a long one was laid out past the edge of the screen with no way
to reach it: the Record Session form lost its file name box and both
buttons, and the "gputaskman not found" page lost its install commands.

A screen using this mixin measures the parts that must stay visible --
titles, hints, errors, buttons -- and caps its scrolling part to the room
they leave, so the bottom of the box is always on screen.
"""

from __future__ import annotations

from textual.css.query import NoMatches
from textual.widget import Widget

# Never squash the scrolling part below this; past here the terminal is
# too short for anything and the body scrolls a few rows at a time.
MIN_BODY = 3


class FitsTerminal:
    """Mixin for a Screen: caps BODY to what the terminal has room for.

    BODY must be able to scroll (a VerticalScroll, OptionList or the like),
    since that is where the content that doesn't fit goes.
    """

    # The part that gives way when there isn't room for everything
    BODY = ".dialog-body"
    # What BODY sits in; None means the screen itself
    BOX = ".dialog"
    # How tall BODY may get when there is room to spare
    BODY_MAX = 24

    def on_mount(self) -> None:
        self.fit_body()
        # Again once the widgets are laid out and have a real height
        self.call_after_refresh(self.fit_body)

    def on_resize(self) -> None:
        self.fit_body()

    def fit_body(self) -> None:
        """Fit the screen to the terminal: stack the buttons if it is narrow,
        then cap the scrolling part to the room the rest of it leaves."""
        self.stack_buttons()

        try:
            box: Widget = self.query_one(self.BOX) if self.BOX else self
            body: Widget = self.query_one(self.BODY)
        except NoMatches:
            return

        used = box.gutter.height + box.styles.margin.height + body.styles.margin.height
        for child in box.children:
            if child is not body and child.display:
                used += child.outer_size.height + child.styles.margin.height

        room = max(MIN_BODY, self.size.height - used)
        body.styles.max_height = min(self.BODY_MAX, room)

    def stack_buttons(self) -> None:
        """Put the buttons one per line when the terminal is too narrow for
        them side by side, so none of them is cut off."""
        for row in self.query(".buttons"):
            buttons = [child for child in row.children if child.display]
            if not buttons or not row.size.width:
                continue
            side_by_side = sum(
                button.outer_size.width + button.styles.margin.width for button in buttons
            )
            row.styles.layout = "vertical" if side_by_side > row.size.width else "horizontal"
