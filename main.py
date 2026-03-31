from gui import TypingGUI

# Start GUI without external sentence file dependency
app = TypingGUI(db_path="typing_master.db")
app.mainloop()