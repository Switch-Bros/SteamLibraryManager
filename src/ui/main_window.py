"""Main Window"""
import customtkinter as ctk
from src.utils.i18n import t
from src.config import config
from src.ui.components.category_tree import CategoryTree

class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title(t('ui.main.title'))
        self.geometry(f"{config.WINDOW_WIDTH}x{config.WINDOW_HEIGHT}")
        ctk.set_appearance_mode(config.THEME)
        
        self._create_ui()
        self._add_test_data()
    
    def _create_ui(self):
        # Menubar
        menu = ctk.CTkFrame(self, height=30, fg_color=("gray85", "gray20"))
        menu.pack(fill="x", side="top")
        ctk.CTkButton(menu, text=t('ui.menu.file'), width=60, 
                     fg_color="transparent").pack(side="left", padx=2)
        self.user_label = ctk.CTkLabel(menu, text=t('ui.status.not_logged_in'))
        self.user_label.pack(side="right", padx=10)
        
        # Toolbar
        toolbar = ctk.CTkFrame(self, height=40, fg_color=("gray90", "gray15"))
        toolbar.pack(fill="x", padx=5, pady=5)
        ctk.CTkButton(toolbar, text="🔄 " + t('ui.toolbar.refresh'), 
                     width=100).pack(side="left", padx=2)
        ctk.CTkButton(toolbar, text="➕ " + t('ui.toolbar.add_category'), 
                     width=120).pack(side="left", padx=2)
        
        # Main Layout
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Left: Categories
        left = ctk.CTkFrame(main, width=250, fg_color="transparent")
        left.pack(side="left", fill="both", padx=(0,5))
        left.pack_propagate(False)
        
        self.cat_tree = CategoryTree(left, on_select=self.on_cat_select)
        self.cat_tree.pack(fill="both", expand=True)
        
        # Middle: Games
        mid = ctk.CTkFrame(main, fg_color="transparent")
        mid.pack(side="left", fill="both", expand=True, padx=5)
        
        search = ctk.CTkFrame(mid, fg_color="transparent", height=35)
        search.pack(fill="x", pady=(0,5))
        search.pack_propagate(False)
        ctk.CTkLabel(search, text="🔍", width=30).pack(side="left")
        ctk.CTkEntry(search, placeholder_text=t('ui.main.search_placeholder')).pack(
            side="left", fill="x", expand=True, padx=5)
        
        games = ctk.CTkScrollableFrame(mid)
        games.pack(fill="both", expand=True)
        ctk.CTkLabel(games, text="Game list will appear here", 
                    font=ctk.CTkFont(size=20)).pack(pady=50)
        
        # Right: Details
        right = ctk.CTkFrame(main, width=350, fg_color=("gray90", "gray15"))
        right.pack(side="left", fill="both", padx=(5,0))
        right.pack_propagate(False)
        ctk.CTkLabel(right, text=t('ui.game_details.title'), 
                    font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        
        # Statusbar
        self.statusbar = ctk.CTkFrame(self, height=25, fg_color=("gray85", "gray20"))
        self.statusbar.pack(fill="x", side="bottom")
        self.status_label = ctk.CTkLabel(self.statusbar, text=t('ui.status.ready'))
        self.status_label.pack(side="left", padx=10)
    
    def _add_test_data(self):
        self.cat_tree.add_category("all_games", 2559, "📁")
        self.cat_tree.add_category("favorites", 23, "⭐")
        self.cat_tree.add_category("uncategorized", 142, "📦")
        self.cat_tree.add_category("Action", 234, "📂")
        self.cat_tree.add_category("RPG", 312, "📂")
    
    def on_cat_select(self, name: str):
        self.status_label.configure(text=f"Selected: {name}")

def main():
    from src.utils.i18n import init_i18n
    init_i18n(config.DEFAULT_LOCALE)
    app = MainWindow()
    app.mainloop()

if __name__ == "__main__":
    main()
