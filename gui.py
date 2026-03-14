import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import threading
import os
from migrate import run_migration
from sync_direct import run_api_sync
from dotenv import load_dotenv

class MigrationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Migração Yampi -> Shopify")
        self.root.geometry("750x650")

        self.create_widgets()

    def log(self, text):
        self.log_area.config(state='normal')
        self.log_area.insert(tk.END, text + "\n")
        self.log_area.see(tk.END)
        self.log_area.config(state='disabled')
        self.root.update_idletasks()

    def create_widgets(self):
        # Frame de Configuração de Preço
        price_frame = ttk.LabelFrame(self.root, text="Controle de Preço (Opcional)", padding=(10, 10))
        price_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        self.price_mode = tk.StringVar(value="none")
        
        ttk.Radiobutton(price_frame, text="Manter Preço Original", variable=self.price_mode, value="none").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        ttk.Radiobutton(price_frame, text="Valor Fixo (R$)", variable=self.price_mode, value="fixed").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        ttk.Radiobutton(price_frame, text="Acréscimo (%)", variable=self.price_mode, value="percentage").grid(row=2, column=0, padx=5, pady=5, sticky="w")

        self.price_value = tk.StringVar()
        ttk.Label(price_frame, text="Valor/Porcentagem: ").grid(row=1, column=1, rowspan=2, padx=5)
        self.price_entry = ttk.Entry(price_frame, textvariable=self.price_value, width=15)
        self.price_entry.grid(row=1, column=2, rowspan=2, padx=5, sticky="w")

        # Frame de Opções de Migração
        mig_frame = ttk.LabelFrame(self.root, text="Migração", padding=(10, 10))
        mig_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")

        # Arquivo Produtos
        ttk.Label(mig_frame, text="Planilha Produtos:").grid(row=0, column=0, sticky="w", padx=5)
        self.products_file_var = tk.StringVar(value="products-69b337642d0b4.xls")
        ttk.Entry(mig_frame, textvariable=self.products_file_var, width=50).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(mig_frame, text="Procurar...", command=lambda: self.browse_file(self.products_file_var)).grid(row=0, column=2, padx=5)

        # Arquivo SKUs
        ttk.Label(mig_frame, text="Planilha SKUs:").grid(row=1, column=0, sticky="w", padx=5)
        self.skus_file_var = tk.StringVar(value="pequenocraque-skus-12_03_2026_19_02_39-ZZQkJ.xlsx")
        ttk.Entry(mig_frame, textvariable=self.skus_file_var, width=50).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(mig_frame, text="Procurar...", command=lambda: self.browse_file(self.skus_file_var)).grid(row=1, column=2, padx=5)

        # Botoes
        btns_frame = ttk.Frame(mig_frame)
        btns_frame.grid(row=2, column=0, columnspan=3, pady=10)

        self.dry_run_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(btns_frame, text="Dry Run (Testar sem Enviar)", variable=self.dry_run_var).pack(side=tk.LEFT, padx=10)
        
        ttk.Button(btns_frame, text="Migrar via Planilhas", command=self.start_excel_migration).pack(side=tk.LEFT, padx=10)
        ttk.Button(btns_frame, text="Sincronizar Direto via API", command=self.start_api_migration).pack(side=tk.LEFT, padx=10)

        # Frame de Logs
        log_frame = ttk.LabelFrame(self.root, text="Logs da Transação", padding=(10, 10))
        log_frame.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")
        self.root.rowconfigure(2, weight=1)
        self.root.columnconfigure(0, weight=1)

        self.log_area = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, state='disabled')
        self.log_area.pack(fill=tk.BOTH, expand=True)

    def browse_file(self, var):
        filepath = filedialog.askopenfilename()
        if filepath:
            var.set(filepath)

    def get_price_modifier(self):
        mode = self.price_mode.get()
        if mode == "none":
            return None
        
        try:
            val = float(self.price_value.get().replace(',', '.'))
            return {"type": mode, "value": val}
        except ValueError:
            messagebox.showerror("Erro de Valor", "Por favor, insira um valor numérico válido no campo de preço.")
            return False

    def check_env(self):
        load_dotenv(override=True)
        if not os.getenv("SHOPIFY_ACCESS_TOKEN") and not os.getenv("SHOPIFY_CLIENT_ID"):
            messagebox.showwarning("Aviso", "O arquivo .env parece estar vazio ou não possuir as credenciais completas. Verifique suas chaves antes de iniciar.")

    def start_excel_migration(self):
        price_mod = self.get_price_modifier()
        if price_mod is False:
            return
        
        prod_file = self.products_file_var.get()
        sku_file = self.skus_file_var.get()
        
        if not prod_file or not sku_file:
            messagebox.showerror("Erro", "Arquivos de produtos e skus obrigatórios.")
            return

        self.check_env()
        self.log("=== INICIANDO MIGRAÇÃO VIA PLANILHA ===")
        dry = self.dry_run_var.get()

        def run():
            try:
                run_migration(prod_file, sku_file, price_modifier=price_mod, log_cb=self.log, dry_run=dry)
            except Exception as e:
                self.log(f"Erro fatal: {str(e)}")
            
        threading.Thread(target=run, daemon=True).start()

    def start_api_migration(self):
        price_mod = self.get_price_modifier()
        if price_mod is False:
            return

        self.check_env()
        self.log("=== INICIANDO SINCRONIZAÇÃO VIA API ===")
        dry = self.dry_run_var.get()

        def run():
            try:
                run_api_sync(price_modifier=price_mod, log_cb=self.log, dry_run=dry)
            except Exception as e:
                self.log(f"Erro fatal: {str(e)}")
            
        threading.Thread(target=run, daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = MigrationApp(root)
    root.mainloop()

