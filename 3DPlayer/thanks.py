import tkinter  # @UnusedImport


class ThanksDialog:

    def __init__(self, parent, main_app):
        self.parent = parent
        self.main_app = main_app
        top = self.top = tkinter.Toplevel(parent)
        top.title("Thanks!!")
        top.protocol("WM_DELETE_WINDOW", self.click_close)

        self.perform_open = False
        row_count = 0

        self.thanks_top_frame = tkinter.Frame(top)
        self.thanks_label = tkinter.Label(
            self.thanks_top_frame,
            text="""I want to say a big thankyou to the following people for helping support this project!\n
Alain""",
        )
        self.thanks_label.pack(padx=5, side=tkinter.LEFT)
        self.thanks_top_frame.grid(row=row_count, column=0, sticky="w")
        row_count += 1

    def click_close(self):
        self.top.destroy()
        self.top = None
