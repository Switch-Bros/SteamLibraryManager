"""Category Tree Widget"""
import customtkinter as ctk
from typing import Optional, Callable
from src.utils.i18n import t

class CategoryTreeItem(ctk.CTkFrame):
    def __init__(self, parent, name: str, count: int, icon: str = "📂", 
                 on_click: Optional[Callable] = None, level: int = 0):
        super().__init__(parent, fg_color="transparent")
        self.name = name
        self.count = count
        self.on_click = on_click
        
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="x", padx=(level*20, 0))
        
        label = ctk.CTkLabel(frame, text=f"{icon} {name} ({count})", anchor="w")
        label.pack(side="left", fill="x", expand=True, padx=5)
        
        frame.bind("<Button-1>", lambda e: self._clicked())
        label.bind("<Button-1>", lambda e: self._clicked())
    
    def _clicked(self):
        if self.on_click:
            self.on_click(self.name)

class CategoryTree(ctk.CTkScrollableFrame):
    def __init__(self, parent, on_select: Optional[Callable] = None):
        super().__init__(parent, fg_color=("gray90", "gray15"))
        self.on_select = on_select
        self.items = {}
        
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(header, text=t('ui.categories.title'), 
                    font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")
    
    def add_category(self, name: str, count: int, icon: str = "📂"):
        item = CategoryTreeItem(self, name, count, icon, on_click=self._on_click)
        item.pack(fill="x", pady=1)
        self.items[name] = item
    
    def _on_click(self, name: str):
        if self.on_select:
            self.on_select(name)
