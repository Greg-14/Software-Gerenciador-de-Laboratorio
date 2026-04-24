import tkinter as tk
from tkinter import messagebox, ttk, font
import sqlite3
from datetime import datetime

# ============================================================
# BANCO DE DADOS
# ============================================================
def iniciar_banco():
    conn = sqlite3.connect("sistema_gmf.db")
    cursor = conn.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS modelos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome_inst TEXT, fabricante TEXT, modelo TEXT)""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS atendimentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT, empresa TEXT, cnpj TEXT, contato TEXT, email TEXT,
        prefixo TEXT, endereco TEXT, cep TEXT, cidade TEXT, uf TEXT,
        ddd_fixo TEXT, tel_fixo TEXT, ddd_cel TEXT, tel_cel TEXT, ativo INTEGER DEFAULT 1)""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS orcamentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT, cliente TEXT, num_orc TEXT, status TEXT)""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS orc_itens (
        id INTEGER PRIMARY KEY AUTOINCREMENT, id_orcamento INTEGER,
        num_item TEXT, descricao TEXT, valor REAL, quantidade INTEGER DEFAULT 1)""")
    # Adicionar coluna quantidade se não existir
    try:
        cursor.execute("ALTER TABLE orc_itens ADD COLUMN quantidade INTEGER DEFAULT 1")
    except:
        pass
    cursor.execute("""CREATE TABLE IF NOT EXISTS ordens_servico (
        id INTEGER PRIMARY KEY AUTOINCREMENT, id_orcamento INTEGER, num_os TEXT,
        modelo_ref TEXT, num_serie TEXT, identificacao TEXT, patrimonio TEXT, fabricante TEXT)""")
    # Adicionar coluna fabricante se não existir
    try:
        cursor.execute("ALTER TABLE ordens_servico ADD COLUMN fabricante TEXT")
    except:
        pass
    conn.commit()
    conn.close()


# ============================================================
# UTILITÁRIOS COMPARTILHADOS
# ============================================================
ESTADOS_CIDADES = {
    "SP": ["São Paulo", "Campinas", "Santos", "S.J. Campos", "Sorocaba", "Ribeirão Preto"],
    "RJ": ["Rio de Janeiro", "Niterói", "Duque de Caxias"],
    "MG": ["Belo Horizonte", "Uberlândia", "Contagem"],
    "PR": ["Curitiba", "Londrina", "Maringá"]
}
PREFIXOS = ["Rua", "Avenida", "Alameda", "Praça", "Rodovia", "Travessa", "Viela", "Loteamento"]
DDDS = sorted([str(i) for i in range(11, 100)])

def ajustar_coluna_auto(tree, col):
    itens = tree.get_children("")
    valores = [str(tree.set(item, col)) for item in itens]
    valores.append(str(col))
    if not valores:
        return
    maior_texto = max(valores, key=len)
    nova_largura = int(len(maior_texto) * 8.5) + 30
    tree.column(col, width=nova_largura)

def gerar_proximo_numero(tabela, campo, separador="-"):
    ano_atual = datetime.now().year
    try:
        conn = sqlite3.connect("sistema_gmf.db"); cursor = conn.cursor()
        cursor.execute(f"SELECT {campo} FROM {tabela} WHERE {campo} LIKE '%{ano_atual}' ORDER BY id DESC LIMIT 1")
        ultimo = cursor.fetchone()
        conn.close()
        num = 1
        if ultimo:
            num = int(ultimo[0].split(separador)[0]) + 1
        return f"{num:03d}{separador}{ano_atual}"
    except:
        return f"001{separador}{ano_atual}"

def formatar_cnpj(event):
    texto = event.widget.get().replace(".", "").replace("/", "").replace("-", "")[:14]
    novo = ""
    for i, c in enumerate(texto):
        if i == 2 or i == 5: novo += "."
        elif i == 8: novo += "/"
        elif i == 12: novo += "-"
        novo += c
    event.widget.delete(0, tk.END); event.widget.insert(0, novo)

def formatar_cep(event):
    texto = event.widget.get().replace("-", "")[:8]
    if len(texto) > 5: texto = f"{texto[:5]}-{texto[5:]}"
    event.widget.delete(0, tk.END); event.widget.insert(0, texto)

def formatar_telefone(event, tipo):
    texto = event.widget.get().replace("-", "")
    if tipo == "fixo" and len(texto) > 4: texto = f"{texto[:4]}-{texto[4:8]}"
    elif tipo == "cel" and len(texto) > 5: texto = f"{texto[:5]}-{texto[5:9]}"
    event.widget.delete(0, tk.END); event.widget.insert(0, texto[:10])

def configurar_autocomplete(cb, lista_valores, somente_lista=True):
    """
    Configura um Combobox com autocomplete:
    - somente_lista=True: só aceita valores da lista (filtra enquanto digita)
    - somente_lista=False: permite digitar livremente mas sugere correspondências
    """
    cb['values'] = lista_valores

    def ao_soltar_tecla(event):
        # Não interfere em teclas de navegação
        if event.keysym in ('Return', 'Escape', 'Tab', 'Up', 'Down', 'Left', 'Right',
                             'Home', 'End', 'Shift_L', 'Shift_R', 'Control_L', 'Control_R'):
            return

        texto_atual = cb.get()
        correspondencias = [v for v in lista_valores
                            if v.lower().startswith(texto_atual.lower())]

        if somente_lista and not correspondencias:
            # Remove o último caractere digitado que não gerou match
            cb.set(texto_atual[:-1])
            cb['values'] = lista_valores
            cb.icursor(tk.END)
            return

        cb['values'] = correspondencias if correspondencias else lista_valores

    def ao_focar(event):
        cb['values'] = lista_valores

    cb.bind('<KeyRelease>', ao_soltar_tecla)
    cb.bind('<FocusIn>', ao_focar)
    cb.bind('<<ComboboxSelected>>', lambda e: cb['values'].__setitem__(slice(None), lista_valores) or None)


# ============================================================
# MÓDULO 1 — MODELOS DE INSTRUMENTOS
# ============================================================
def abrir_janela_modelos(pai=None):
    if pai is None:
        janela_mod = tk.Toplevel()
        janela_mod.title("Modelos de Instrumentos - GMF")
        janela_mod.geometry("800x500")
        janela_mod.grab_set()
    else:
        for w in pai.winfo_children(): w.destroy()
        janela_mod = pai

    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Treeview.Heading", background="#4a90e2", foreground="white", font=("Arial", 10, "bold"))
    style.map("Treeview.Heading", background=[('active', '#357abd')])

    def ordenar_coluna(col, reverse):
        l = [(tab.set(k, col), k) for k in tab.get_children('')]
        l.sort(reverse=reverse)
        for index, (val, k) in enumerate(l):
            tab.move(k, '', index)
        tab.heading("Instrumento", text="Instrumento")
        tab.heading("Fabricante", text="Fabricante")
        tab.heading("Modelo", text="Modelo")
        seta = "▼" if reverse else "▲"
        titulo_com_seta = f"{col.ljust(28)}{seta}"
        tab.heading(col, text=titulo_com_seta, command=lambda: ordenar_coluna(col, not reverse))

    def atualizar_filtros_e_tabela(event=None):
        for i in tab.get_children(): tab.delete(i)
        conn = sqlite3.connect("sistema_gmf.db"); cursor = conn.cursor()
        query = "SELECT id, nome_inst, fabricante, modelo FROM modelos WHERE 1=1"
        params = []
        if cb_n.get().strip():
            query += " AND nome_inst LIKE ?"; params.append(f"%{cb_n.get()}%")
        if cb_f.get().strip():
            query += " AND fabricante LIKE ?"; params.append(f"%{cb_f.get()}%")
        if cb_m.get().strip():
            query += " AND modelo LIKE ?"; params.append(f"%{cb_m.get()}%")
        cursor.execute(query, params)
        rows = cursor.fetchall()
        for r in rows: tab.insert("", tk.END, values=r)
        lbl_total.config(text=f"Total de modelos = {len(rows)}")
        cursor.execute("SELECT DISTINCT nome_inst FROM modelos ORDER BY nome_inst")
        lista_n = [i[0] for i in cursor.fetchall()]
        cb_n['values'] = lista_n
        cursor.execute("SELECT DISTINCT fabricante FROM modelos ORDER BY fabricante")
        lista_f = [i[0] for i in cursor.fetchall()]
        cb_f['values'] = lista_f
        cursor.execute("SELECT DISTINCT modelo FROM modelos ORDER BY modelo")
        lista_m = [i[0] for i in cursor.fetchall()]
        cb_m['values'] = lista_m
        conn.close()
        # Fim de atualizar_filtros_e_tabela

    def formulario_instrumento(id_mod=None, dados=None):
        titulo = "Editar Instrumento" if id_mod else "Novo Instrumento"
        jan_f = tk.Toplevel(); jan_f.title(titulo); jan_f.geometry("380x320"); jan_f.grab_set()
        conn2 = sqlite3.connect("sistema_gmf.db"); cursor2 = conn2.cursor()
        cursor2.execute("SELECT DISTINCT nome_inst FROM modelos ORDER BY nome_inst")
        lista_inst = [r[0] for r in cursor2.fetchall()]
        cursor2.execute("SELECT DISTINCT fabricante FROM modelos ORDER BY fabricante")
        lista_fab = [r[0] for r in cursor2.fetchall()]
        cursor2.execute("SELECT DISTINCT modelo FROM modelos ORDER BY modelo")
        lista_mod = [r[0] for r in cursor2.fetchall()]
        conn2.close()
        tk.Label(jan_f, text="Instrumento:").pack()
        e1 = ttk.Combobox(jan_f, width=33); e1.pack(pady=5)
        configurar_autocomplete(e1, lista_inst, somente_lista=False)
        tk.Label(jan_f, text="Fabricante:").pack()
        e2 = ttk.Combobox(jan_f, width=33); e2.pack(pady=5)
        configurar_autocomplete(e2, lista_fab, somente_lista=False)
        tk.Label(jan_f, text="Modelo:").pack()
        e3 = ttk.Combobox(jan_f, width=33); e3.pack(pady=5)
        configurar_autocomplete(e3, lista_mod, somente_lista=False)
        if dados:
            e1.set(dados[1]); e2.set(dados[2]); e3.set(dados[3])

        def gravar():
            if not e1.get(): return messagebox.showwarning("Aviso", "Nome é obrigatório")
            conn2 = sqlite3.connect("sistema_gmf.db"); cursor2 = conn2.cursor()
            if id_mod:
                cursor2.execute("UPDATE modelos SET nome_inst=?, fabricante=?, modelo=? WHERE id=?",
                               (e1.get(), e2.get(), e3.get(), id_mod))
            else:
                cursor2.execute("INSERT INTO modelos (nome_inst, fabricante, modelo) VALUES (?,?,?)",
                               (e1.get(), e2.get(), e3.get()))
            conn2.commit(); conn2.close(); jan_f.destroy(); atualizar_filtros_e_tabela()
        tk.Button(jan_f, text="GRAVAR", command=gravar, bg="#28a745", fg="white", width=15).pack(pady=10)

    def acao_editar():
        sel = tab.selection()
        if not sel: return
        dados = tab.item(sel)['values']
        formulario_instrumento(id_mod=dados[0], dados=dados)

    def acao_excluir():
        sel = tab.selection()
        if not sel: return
        if messagebox.askyesno("Confirmar", "Excluir permanentemente?"):
            id_sel = tab.item(sel)['values'][0]
            conn = sqlite3.connect("sistema_gmf.db"); cursor = conn.cursor()
            cursor.execute("DELETE FROM modelos WHERE id=?", (id_sel,))
            conn.commit(); conn.close(); atualizar_filtros_e_tabela()

    f_cima = tk.LabelFrame(janela_mod, text=" Filtros de Busca ", padx=10, pady=10)
    f_cima.pack(fill="x", padx=10, pady=10)
    cb_n = ttk.Combobox(f_cima, width=22, state="readonly"); cb_n.grid(row=1, column=0, padx=5)
    cb_f = ttk.Combobox(f_cima, width=22, state="readonly"); cb_f.grid(row=1, column=1, padx=5)
    cb_m = ttk.Combobox(f_cima, width=22, state="readonly"); cb_m.grid(row=1, column=2, padx=5)
    for cb in [cb_n, cb_f, cb_m]:
        cb.bind("<KeyRelease>", atualizar_filtros_e_tabela)
        cb.bind("<<ComboboxSelected>>", atualizar_filtros_e_tabela)
    for i, txt in enumerate(["Instrumento", "Fabricante", "Modelo"]):
        tk.Label(f_cima, text=txt).grid(row=0, column=i)
    tk.Button(f_cima, text="LIMPAR",
              command=lambda: [cb_n.set(''), cb_f.set(''), cb_m.set(''), atualizar_filtros_e_tabela()]
              ).grid(row=1, column=3, padx=5)

    f_corpo = tk.Frame(janela_mod); f_corpo.pack(fill="both", expand=True, padx=10)
    scroll_y = ttk.Scrollbar(f_corpo, orient="vertical")
    tab = ttk.Treeview(f_corpo, columns=("ID", "Instrumento", "Fabricante", "Modelo"),
                       show="headings", yscrollcommand=scroll_y.set)
    scroll_y.config(command=tab.yview); scroll_y.pack(side="right", fill="y")
    for col in ["Instrumento", "Fabricante", "Modelo"]:
        tab.heading(col, text=col, command=lambda _c=col: ordenar_coluna(_c, False))
        tab.column(col, width=200)
    tab.column("ID", width=0, stretch=tk.NO)
    tab.pack(side="left", fill="both", expand=True)

    f_btns = tk.Frame(f_corpo); f_btns.pack(side="left", fill="y", padx=5)
    tk.Button(f_btns, text="+", command=lambda: formulario_instrumento(),
              bg="#28a745", fg="white", font=("Arial", 12, "bold"), width=3).pack(pady=2)
    tk.Button(f_btns, text="-", command=acao_excluir,
              bg="#dc3545", fg="white", font=("Arial", 12, "bold"), width=3).pack(pady=2)
    tk.Button(f_btns, text="✎", command=acao_editar,
              bg="#ffc107", fg="black", font=("Arial", 12, "bold"), width=3).pack(pady=2)

    tab.bind("<Double-1>", lambda e: acao_editar())
    f_rodape = tk.Frame(janela_mod, padx=20, pady=10); f_rodape.pack(fill="x")
    lbl_total = tk.Label(f_rodape, text="Total de modelos = 0", font=("Arial", 10, "bold"))
    lbl_total.pack(side="right")
    atualizar_filtros_e_tabela()


# ============================================================
# MÓDULO 2 — CADASTRO DE CLIENTES
# ============================================================
def janela_formulario_cliente(id_cli=None, dados=None, callback=None):
    jan = tk.Toplevel()
    jan.title("Ficha do Cliente")
    jan.geometry("750x580")
    jan.grab_set()

    f = tk.Frame(jan, padx=15, pady=10); f.pack(fill="both", expand=True)

    tk.Label(f, text="Empresa:").grid(row=0, column=0, sticky="w")
    e_emp = tk.Entry(f, width=35); e_emp.grid(row=1, column=0, padx=5, pady=2, sticky="w")
    tk.Label(f, text="Contato:").grid(row=0, column=1, sticky="w")
    e_cont = tk.Entry(f, width=30); e_cont.grid(row=1, column=1, padx=5, pady=2, sticky="w")

    tk.Label(f, text="CNPJ:").grid(row=2, column=0, sticky="w")
    e_cnpj = tk.Entry(f, width=35); e_cnpj.grid(row=3, column=0, padx=5, pady=5, sticky="w")
    e_cnpj.bind("<KeyRelease>", formatar_cnpj)
    tk.Label(f, text="Email:").grid(row=2, column=1, sticky="w")
    e_mail = tk.Entry(f, width=30); e_mail.grid(row=3, column=1, padx=5, pady=5, sticky="w")

    tk.Label(f, text="Prefixo:").grid(row=4, column=0, sticky="w")
    cb_pre = ttk.Combobox(f, values=PREFIXOS, width=15); cb_pre.grid(row=5, column=0, padx=5, pady=5, sticky="w")
    configurar_autocomplete(cb_pre, PREFIXOS, somente_lista=True)
    tk.Label(f, text="Endereço:").grid(row=4, column=1, sticky="w")
    e_end = tk.Entry(f, width=30); e_end.grid(row=5, column=1, padx=5, pady=5, sticky="w")

    tk.Label(f, text="CEP:").grid(row=6, column=0, sticky="w")
    e_cep = tk.Entry(f, width=18); e_cep.grid(row=7, column=0, sticky="w", padx=5)
    e_cep.bind("<KeyRelease>", formatar_cep)
    tk.Label(f, text="UF:").grid(row=6, column=1, sticky="w")
    lista_ufs = list(ESTADOS_CIDADES.keys())
    cb_uf = ttk.Combobox(f, values=lista_ufs, width=10)
    cb_uf.grid(row=7, column=1, sticky="w", padx=5)
    configurar_autocomplete(cb_uf, lista_ufs, somente_lista=True)

    tk.Label(f, text="Cidade:").grid(row=8, column=0, sticky="w")
    cb_cit = ttk.Combobox(f, width=32); cb_cit.grid(row=9, column=0, padx=5, pady=5, sticky="w")

    def ao_mudar_uf(event=None):
        cidades = ESTADOS_CIDADES.get(cb_uf.get(), [])
        cb_cit.config(values=cidades)
        configurar_autocomplete(cb_cit, cidades, somente_lista=False)
    cb_uf.bind("<<ComboboxSelected>>", ao_mudar_uf)

    tk.Label(f, text="Telefone Fixo:").grid(row=10, column=0, sticky="w")
    f_fixo = tk.Frame(f); f_fixo.grid(row=11, column=0, sticky="w", padx=5)
    cb_df = ttk.Combobox(f_fixo, values=DDDS, width=5); cb_df.set("11"); cb_df.pack(side="left")
    configurar_autocomplete(cb_df, DDDS, somente_lista=True)
    e_fixo = tk.Entry(f_fixo, width=18); e_fixo.pack(side="left", padx=5)
    e_fixo.bind("<KeyRelease>", lambda e: formatar_telefone(e, "fixo"))

    tk.Label(f, text="Celular:").grid(row=10, column=1, sticky="w")
    f_cel = tk.Frame(f); f_cel.grid(row=11, column=1, sticky="w", padx=5)
    cb_dc = ttk.Combobox(f_cel, values=DDDS, width=5); cb_dc.set("11"); cb_dc.pack(side="left")
    configurar_autocomplete(cb_dc, DDDS, somente_lista=True)
    e_cel = tk.Entry(f_cel, width=18); e_cel.pack(side="left", padx=5)
    e_cel.bind("<KeyRelease>", lambda e: formatar_telefone(e, "cel"))

    var_ativo = tk.IntVar(value=1)
    tk.Checkbutton(f, text="Ativo", variable=var_ativo).grid(row=13, column=0, sticky="w", padx=5, pady=10)

    if dados:
        e_emp.insert(0, dados[1]); e_cnpj.insert(0, dados[2]); e_cont.insert(0, dados[3])
        e_mail.insert(0, dados[4]); cb_pre.set(dados[5]); e_end.insert(0, dados[6])
        e_cep.insert(0, dados[7])
        cb_cit.config(values=ESTADOS_CIDADES.get(dados[9], [])); cb_cit.set(dados[8]); cb_uf.set(dados[9])
        cb_df.set(dados[10]); e_fixo.insert(0, dados[11]); cb_dc.set(dados[12])
        e_cel.insert(0, dados[13]); var_ativo.set(dados[14])

    def salvar():
        conn = sqlite3.connect("sistema_gmf.db"); cursor = conn.cursor()
        v = (e_emp.get(), e_cnpj.get(), e_cont.get(), e_mail.get(), cb_pre.get(), e_end.get(),
             e_cep.get(), cb_cit.get(), cb_uf.get(), cb_df.get(), e_fixo.get(),
             cb_dc.get(), e_cel.get(), var_ativo.get())
        if id_cli:
            cursor.execute("""UPDATE atendimentos SET empresa=?, cnpj=?, contato=?, email=?, prefixo=?,
                              endereco=?, cep=?, cidade=?, uf=?, ddd_fixo=?, tel_fixo=?,
                              ddd_cel=?, tel_cel=?, ativo=? WHERE id=?""", (*v, id_cli))
        else:
            cursor.execute("""INSERT INTO atendimentos (empresa, cnpj, contato, email, prefixo, endereco,
                              cep, cidade, uf, ddd_fixo, tel_fixo, ddd_cel, tel_cel, ativo)
                              VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", v)
        conn.commit(); conn.close()
        if callback: callback()
        jan.destroy()

    tk.Button(jan, text="SALVAR DADOS", command=salvar,
              bg="#28a745", fg="white", font=("Arial", 9, "bold")).pack(pady=10)

def janela_visualizar_cliente(id_cli, callback_refresh):
    conn = sqlite3.connect("sistema_gmf.db"); cursor = conn.cursor()
    cursor.execute("SELECT * FROM atendimentos WHERE id=?", (id_cli,))
    dados = cursor.fetchone(); conn.close()
    if not dados: return
    vis = tk.Toplevel(); vis.title("Dados do Cliente"); vis.geometry("450x520")
    container = tk.Frame(vis, padx=20, pady=15); container.pack(fill="both")
    status = "ATIVO" if dados[14] == 1 else "INATIVO"
    campos = [("Status", status), ("Empresa", dados[1]), ("CNPJ", dados[2]), ("Contato", dados[3]),
              ("Email", dados[4]), ("Endereço", f"{dados[5]} {dados[6]}"), ("CEP", dados[7]),
              ("Cidade/UF", f"{dados[8]} - {dados[9]}"),
              ("Tel. Fixo", f"({dados[10]}) {dados[11]}"), ("Celular", f"({dados[12]}) {dados[13]}")]
    for label, valor in campos:
        f_line = tk.Frame(container); f_line.pack(fill="x", pady=3)
        tk.Label(f_line, text=f"{label}:", font=("Arial", 9, "bold")).pack(side="left")
        tk.Label(f_line, text=f" {valor}", font=("Arial", 9)).pack(side="left")
    tk.Button(vis, text="EDITAR DADOS",
              command=lambda: [vis.destroy(), janela_formulario_cliente(id_cli, dados, callback_refresh)],
              bg="#007bff", fg="white", font=("Arial", 9, "bold")).pack(side="bottom", pady=15)

def abrir_cadastro(pai=None):
    if pai is None:
        janela_cad = tk.Toplevel()
        janela_cad.title("Gestão de Clientes - GMF")
        janela_cad.geometry("950x500")
    else:
        for w in pai.winfo_children(): w.destroy()
        janela_cad = pai

    colunas = ("ID", "Empresa", "CNPJ", "Contato", "Email", "Endereço", "CEP", "Cidade", "UF", "Fixo", "Celular")

    def auto_ajustar_uma_coluna(col):
        f_font = font.Font(family="Arial", size=10)
        largura = f_font.measure(col) + 30
        for item in tab.get_children():
            idx = colunas.index(col)
            val = str(tab.item(item)['values'][idx])
            larg_val = f_font.measure(val) + 25
            if larg_val > largura: largura = larg_val
        tab.column(col, width=largura)

    def ajustar_todas_colunas():
        for col in colunas: auto_ajustar_uma_coluna(col)

    def on_header_double_click(event):
        region = tab.identify_region(event.x, event.y)
        if region == "separator":
            column_id = tab.identify_column(event.x)
            col_idx = int(column_id.replace('#', '')) - 1
            auto_ajustar_uma_coluna(colunas[col_idx])

    def atualizar_tabela():
        for i in tab.get_children(): tab.delete(i)
        conn = sqlite3.connect("sistema_gmf.db"); cursor = conn.cursor()
        query = "SELECT * FROM atendimentos WHERE empresa LIKE ? AND cnpj LIKE ?"
        params = [f'%{ent_f_emp.get()}%', f'%{ent_f_cnpj.get()}%']
        if cb_f_status.get() == "Ativos": query += " AND ativo = 1"
        elif cb_f_status.get() == "Inativos": query += " AND ativo = 0"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        for r in rows:
            tab.insert("", tk.END, values=(
                r[0], r[1], r[2], r[3], r[4],
                f"{r[5]} {r[6]}", r[7], r[8], r[9],
                f"({r[10]}) {r[11]}", f"({r[12]}) {r[13]}"))
        conn.close()
        ajustar_todas_colunas()
        lbl_total.config(text=f"Total de clientes: {len(rows)}")

    def carregar_opcoes_filtro():
        conn = sqlite3.connect("sistema_gmf.db"); cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT empresa FROM atendimentos ORDER BY empresa")
        lista_emp = [r[0] for r in cursor.fetchall()]
        cursor.execute("SELECT DISTINCT cnpj FROM atendimentos ORDER BY cnpj")
        lista_cnpj = [r[0] for r in cursor.fetchall()]
        conn.close()
        return lista_emp, lista_cnpj

    f_filtros = tk.LabelFrame(janela_cad, text=" Filtros de Busca ", padx=10, pady=10)
    f_filtros.pack(fill="x", padx=10, pady=5)
    tk.Label(f_filtros, text="Empresa:").grid(row=0, column=0)
    ent_f_emp = ttk.Combobox(f_filtros, width=25); ent_f_emp.grid(row=0, column=1, padx=5)
    tk.Label(f_filtros, text="CNPJ:").grid(row=0, column=2)
    ent_f_cnpj = ttk.Combobox(f_filtros, width=20); ent_f_cnpj.grid(row=0, column=3, padx=5)
    cb_f_status = ttk.Combobox(f_filtros, values=["Todos", "Ativos", "Inativos"], width=10)
    cb_f_status.set("Todos"); cb_f_status.grid(row=0, column=5, padx=5)
    cb_f_status.bind("<<ComboboxSelected>>", lambda e: atualizar_tabela())
    lista_emp_f, lista_cnpj_f = carregar_opcoes_filtro()
    ent_f_emp.config(state="readonly"); ent_f_emp['values'] = lista_emp_f
    ent_f_cnpj.config(state="readonly"); ent_f_cnpj['values'] = lista_cnpj_f

    # Digitação rápida: acumula letras e salta para o match
    _buf_emp = [""]; _buf_cnpj = [""]
    def jump_tipo(cb, buf, lista, event):
        ch = event.char
        if not ch or not ch.isprintable(): return
        buf[0] += ch.lower()
        matches = [v for v in lista if v.lower().startswith(buf[0])]
        if not matches:
            buf[0] = ch.lower()
            matches = [v for v in lista if v.lower().startswith(buf[0])]
        if matches:
            cb.set(matches[0]); cb.event_generate("<<ComboboxSelected>>")
        janela_cad.after(800, lambda: buf.__setitem__(0, ""))
    ent_f_emp.bind("<KeyPress>", lambda e: jump_tipo(ent_f_emp, _buf_emp, lista_emp_f, e))
    ent_f_cnpj.bind("<KeyPress>", lambda e: jump_tipo(ent_f_cnpj, _buf_cnpj, lista_cnpj_f, e))
    ent_f_emp.bind("<<ComboboxSelected>>", lambda e: atualizar_tabela())
    ent_f_cnpj.bind("<<ComboboxSelected>>", lambda e: atualizar_tabela())

    f_rodape = tk.Frame(janela_cad, padx=10, pady=5); f_rodape.pack(fill="x", side="bottom")
    lbl_total = tk.Label(f_rodape, text="Total de clientes: 0", font=("Arial", 9, "bold"))
    lbl_total.pack(side="right")

    f_main = tk.Frame(janela_cad); f_main.pack(fill="both", expand=True, padx=10, pady=5)

    f_btns = tk.Frame(f_main, padx=5); f_btns.pack(side="right", fill="y")
    tk.Button(f_btns, text="+",
              command=lambda: janela_formulario_cliente(callback=atualizar_tabela),
              bg="#28a745", fg="white", font=("Arial", 11, "bold"), width=3).pack(pady=2)

    def acao_excluir_cli():
        sel = tab.selection()
        if sel and messagebox.askyesno("Confirmar", "Excluir registro?"):
            id_sel = tab.item(sel)['values'][0]
            conn = sqlite3.connect("sistema_gmf.db"); cursor = conn.cursor()
            cursor.execute("DELETE FROM atendimentos WHERE id=?", (id_sel,))
            conn.commit(); conn.close(); atualizar_tabela()

    tk.Button(f_btns, text="-", command=acao_excluir_cli,
              bg="#dc3545", fg="white", font=("Arial", 11, "bold"), width=3).pack(pady=2)

    def acao_editar_cli():
        sel = tab.selection()
        if sel:
            id_sel = tab.item(sel)['values'][0]
            conn = sqlite3.connect("sistema_gmf.db"); cursor = conn.cursor()
            cursor.execute("SELECT * FROM atendimentos WHERE id=?", (id_sel,))
            d = cursor.fetchone(); conn.close()
            janela_formulario_cliente(id_cli=id_sel, dados=d, callback=atualizar_tabela)

    tk.Button(f_btns, text="✎", command=acao_editar_cli,
              bg="#ffc107", fg="black", font=("Arial", 11, "bold"), width=3).pack(pady=2)

    f_tabela_container = tk.Frame(f_main); f_tabela_container.pack(side="left", fill="both", expand=True)
    scroll_y = tk.Scrollbar(f_tabela_container, orient="vertical")
    scroll_x = tk.Scrollbar(f_tabela_container, orient="horizontal")
    tab = ttk.Treeview(f_tabela_container, columns=colunas, show="headings",
                       yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
    scroll_y.config(command=tab.yview); scroll_y.pack(side="right", fill="y")
    scroll_x.config(command=tab.xview); scroll_x.pack(side="bottom", fill="x")
    for c in colunas: tab.heading(c, text=c)
    tab.column("ID", width=0, stretch=tk.NO)
    tab.pack(side="left", fill="both", expand=True)

    tab.bind("<Double-1>", lambda e: janela_visualizar_cliente(
        tab.item(tab.selection())['values'][0], atualizar_tabela)
        if tab.identify_region(e.x, e.y) == "cell" and tab.selection() else None)
    tab.bind("<Double-Button-1>", on_header_double_click, add="+")

    atualizar_tabela()


# ============================================================
# MÓDULO 3 — ORÇAMENTOS
# ============================================================
def abrir_detalhes_orcamento(id_orc_existente=None, callback_atualizar=None):
    jan_detalhe = tk.Toplevel()
    jan_detalhe.title("Detalhes do Orçamento - GMF")
    jan_detalhe.geometry("1000x620")
    jan_detalhe.grab_set()

    id_orc_atual = [id_orc_existente]
    style = ttk.Style(); style.theme_use("clam")
    style.configure("Treeview.Heading", background="#4a90e2", foreground="white", font=("Arial", 10, "bold"))

    f_head = tk.Frame(jan_detalhe, pady=10); f_head.pack(fill="x", padx=10)
    tk.Label(f_head, text="Nº Orçamento:").grid(row=0, column=0, sticky="w")
    ent_num = tk.Entry(f_head, width=15); ent_num.grid(row=1, column=0, padx=5, pady=5)

    tk.Label(f_head, text="Cliente:").grid(row=0, column=1, sticky="w")
    cb_cli = ttk.Combobox(f_head, width=45); cb_cli.grid(row=1, column=1, padx=5)
    conn_cli = sqlite3.connect("sistema_gmf.db"); cursor_cli = conn_cli.cursor()
    cursor_cli.execute("SELECT DISTINCT empresa FROM atendimentos ORDER BY empresa")
    lista_clientes_orc = [r[0] for r in cursor_cli.fetchall()]; conn_cli.close()
    configurar_autocomplete(cb_cli, lista_clientes_orc, somente_lista=False)

    tk.Label(f_head, text="Status:").grid(row=0, column=2, sticky="w")
    cb_st = ttk.Combobox(f_head, values=["Aguardando aprovação", "Aprovado", "Não Aprovado", "Cancelado"], width=25)
    cb_st.grid(row=1, column=2, padx=5); cb_st.set("Aguardando aprovação")

    def bloquear_campos():
        if id_orc_atual[0]:
            ent_num.config(state="disabled")
            cb_cli.config(state="disabled")

    if id_orc_atual[0]:
        conn = sqlite3.connect("sistema_gmf.db"); cursor = conn.cursor()
        cursor.execute("SELECT cliente, num_orc, status FROM orcamentos WHERE id=?", (id_orc_atual[0],))
        dados = cursor.fetchone()
        if dados:
            cb_cli.set(dados[0]); ent_num.insert(0, dados[1]); cb_st.set(dados[2])
        conn.close()
        bloquear_campos()
    else:
        ent_num.insert(0, gerar_proximo_numero("orcamentos", "num_orc", "-"))

    nb = ttk.Notebook(jan_detalhe); nb.pack(fill="both", expand=True, padx=10, pady=10)
    f_it = tk.Frame(nb); f_os = tk.Frame(nb)
    nb.add(f_it, text=" Itens do Orçamento "); nb.add(f_os, text=" Ordens de Serviço ")

    def salvar_orcamento_pai():
        conn = sqlite3.connect("sistema_gmf.db"); cursor = conn.cursor()
        if not id_orc_atual[0]:
            cursor.execute("INSERT INTO orcamentos (cliente, num_orc, status) VALUES (?,?,?)",
                           (cb_cli.get(), ent_num.get(), cb_st.get()))
            id_orc_atual[0] = cursor.lastrowid
            bloquear_campos()
        else:
            cursor.execute("UPDATE orcamentos SET status=? WHERE id=?", (cb_st.get(), id_orc_atual[0]))
        conn.commit(); conn.close()
        if callback_atualizar: callback_atualizar()

    # --- ABA ITENS ---
    def carregar_itens():
        for i in tab_it.get_children(): tab_it.delete(i)
        if not id_orc_atual[0]: return
        conn = sqlite3.connect("sistema_gmf.db"); cursor = conn.cursor()
        cursor.execute("SELECT id, num_item, descricao, valor, COALESCE(quantidade,1) FROM orc_itens WHERE id_orcamento=?",
                       (id_orc_atual[0],))
        total_geral = 0.0
        total_qtd = 0
        for r in cursor.fetchall():
            qtd = r[4] if r[4] else 1
            total_linha = r[3] * qtd
            total_geral += total_linha
            total_qtd += qtd
            tab_it.insert("", tk.END, values=(r[0], r[1], r[2], qtd, f"R$ {r[3]:.2f}", f"R$ {total_linha:.2f}"))
        conn.close()
        lbl_total_itens.config(text=f"Total de equipamentos: {total_qtd}   |   Valor Total: R$ {total_geral:.2f}")

    def add_item(id_item=None):
        jan_i = tk.Toplevel(jan_detalhe); jan_i.title("Item"); jan_i.geometry("450x380"); jan_i.grab_set()
        tk.Label(jan_i, text="Nº:").pack()
        e_n = tk.Entry(jan_i, justify="center"); e_n.pack()
        tk.Label(jan_i, text="Descrição:").pack()
        c_t = ttk.Combobox(jan_i, values=["Calibração (RBC) em", "Calibração Rastreada em"], width=35)
        c_t.pack(); c_t.set("Calibração (RBC) em")
        c_m = ttk.Combobox(jan_i, width=35); c_m.pack()
        conn = sqlite3.connect("sistema_gmf.db"); cursor = conn.cursor()
        cursor.execute("SELECT nome_inst || ' ' || modelo FROM modelos")
        lista_modelos_item = [r[0] for r in cursor.fetchall()]; conn.close()
        c_m['values'] = lista_modelos_item
        configurar_autocomplete(c_m, lista_modelos_item, somente_lista=False)
        tk.Label(jan_i, text="Quantidade:").pack()
        e_q = tk.Entry(jan_i, justify="center", width=10); e_q.pack(); e_q.insert(0, "1")
        tk.Label(jan_i, text="Valor unitário (R$):").pack()
        e_v = tk.Entry(jan_i); e_v.pack()

        if id_item:
            conn = sqlite3.connect("sistema_gmf.db"); cursor = conn.cursor()
            cursor.execute("SELECT num_item, descricao, valor, COALESCE(quantidade,1) FROM orc_itens WHERE id=?", (id_item,))
            d = cursor.fetchone(); conn.close()
            if d:
                e_n.insert(0, d[0])
                partes = d[1].split(" ", 3)
                if len(partes) >= 4:
                    c_t.set(f"{partes[0]} {partes[1]}")
                    c_m.set(partes[3])
                e_v.insert(0, str(d[2]))
                e_q.delete(0, tk.END); e_q.insert(0, str(d[3]))
        else:
            # Número automático crescente
            if id_orc_atual[0]:
                conn2 = sqlite3.connect("sistema_gmf.db"); cur2 = conn2.cursor()
                cur2.execute("SELECT COUNT(*) FROM orc_itens WHERE id_orcamento=?", (id_orc_atual[0],))
                count_it = cur2.fetchone()[0]; conn2.close()
            else:
                count_it = 0
            e_n.insert(0, str(count_it + 1))

        def gravar():
            salvar_orcamento_pai()
            desc = f"{c_t.get()} {c_m.get()}"
            conn = sqlite3.connect("sistema_gmf.db"); cursor = conn.cursor()
            v_val = e_v.get().replace(",", ".")
            try: qtd = int(e_q.get())
            except: qtd = 1
            if id_item:
                cursor.execute("UPDATE orc_itens SET num_item=?, descricao=?, valor=?, quantidade=? WHERE id=?",
                               (e_n.get(), desc, float(v_val), qtd, id_item))
            else:
                cursor.execute("INSERT INTO orc_itens (id_orcamento, num_item, descricao, valor, quantidade) VALUES (?,?,?,?,?)",
                               (id_orc_atual[0], e_n.get(), desc, float(v_val), qtd))
            conn.commit(); conn.close(); jan_i.destroy(); carregar_itens()
        tk.Button(jan_i, text="GRAVAR ITEM", command=gravar, bg="#28a745", fg="white").pack(pady=20)

    f_tab_it = tk.Frame(f_it); f_tab_it.pack(side="left", fill="both", expand=True)
    tab_it = ttk.Treeview(f_tab_it, columns=("ID", "Nº", "Descrição", "Qtd", "Valor Unit.", "Valor Total"), show="headings")
    for c in [("ID", 0), ("Nº", 45), ("Descrição", 370), ("Qtd", 45), ("Valor Unit.", 110), ("Valor Total", 110)]:
        tab_it.heading(c[0], text=c[0], command=lambda _c=c[0]: ajustar_coluna_auto(tab_it, _c))
        tab_it.column(c[0], width=c[1], stretch=tk.NO if c[0] in ("ID", "Nº", "Qtd", "Valor Unit.", "Valor Total") else tk.YES)
    tab_it.pack(fill="both", expand=True)
    tab_it.bind("<Double-1>", lambda e: add_item(tab_it.item(tab_it.selection())['values'][0]))
    lbl_total_itens = tk.Label(f_tab_it, text="Total de itens: 0   |   Valor Total: R$ 0,00",
                               font=("Arial", 9, "bold"), anchor="e")
    lbl_total_itens.pack(fill="x", pady=2)

    f_b_it = tk.Frame(f_it); f_b_it.pack(side="right", fill="y", padx=5)
    tk.Button(f_b_it, text="+", bg="#28a745", fg="white", font=("Arial", 12, "bold"), width=3,
              command=add_item).pack(pady=2)

    def excluir_item():
        sel = tab_it.selection()
        if not sel: return
        id_del = tab_it.item(sel)['values'][0]
        conn = sqlite3.connect("sistema_gmf.db"); cursor = conn.cursor()
        cursor.execute("DELETE FROM orc_itens WHERE id=?", (id_del,))
        conn.commit(); conn.close(); carregar_itens()

    tk.Button(f_b_it, text="-", bg="#dc3545", fg="white", font=("Arial", 12, "bold"), width=3,
              command=excluir_item).pack(pady=2)
    tk.Button(f_b_it, text="✎", bg="#ffc107", font=("Arial", 12, "bold"), width=3,
              command=lambda: add_item(tab_it.item(tab_it.selection())['values'][0])).pack(pady=2)

    # --- ABA OS ---
    def carregar_os():
        for i in tab_os.get_children(): tab_os.delete(i)
        if not id_orc_atual[0]: return
        conn = sqlite3.connect("sistema_gmf.db"); cursor = conn.cursor()
        cursor.execute("""SELECT id, num_os, COALESCE(fabricante,''), modelo_ref, num_serie, identificacao, patrimonio
                          FROM ordens_servico WHERE id_orcamento=?""", (id_orc_atual[0],))
        rows = cursor.fetchall()
        for r in rows: tab_os.insert("", tk.END, values=r)
        conn.close()
        lbl_total_os.config(text=f"Total de OS: {len(rows)}")

    def add_os(id_os=None):
        # Verificar limite de OS baseado na quantidade total de equipamentos
        if not id_os and id_orc_atual[0]:
            conn_chk = sqlite3.connect("sistema_gmf.db"); cur_chk = conn_chk.cursor()
            cur_chk.execute("SELECT COALESCE(SUM(COALESCE(quantidade,1)),0) FROM orc_itens WHERE id_orcamento=?", (id_orc_atual[0],))
            max_os = cur_chk.fetchone()[0]
            cur_chk.execute("SELECT COUNT(*) FROM ordens_servico WHERE id_orcamento=?", (id_orc_atual[0],))
            atual_os = cur_chk.fetchone()[0]
            conn_chk.close()
            if atual_os >= max_os:
                messagebox.showwarning("Limite atingido",
                    f"Já existem {atual_os} OS cadastradas.\n"
                    f"O limite é {max_os} (total de equipamentos nos itens do orçamento).")
                return
        jan_o = tk.Toplevel(jan_detalhe); jan_o.title("Ordem de Serviço")
        jan_o.geometry("400x520"); jan_o.grab_set()
        tk.Label(jan_o, text="Número de Os:").pack(pady=5)
        e_o = tk.Entry(jan_o, width=30); e_o.pack()
        tk.Label(jan_o, text="Fabricante:").pack(pady=5)
        c_fab = ttk.Combobox(jan_o, width=27); c_fab.pack()
        conn = sqlite3.connect("sistema_gmf.db"); cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT fabricante FROM modelos ORDER BY fabricante")
        lista_fab_os = [r[0] for r in cursor.fetchall()]
        c_fab['values'] = lista_fab_os
        configurar_autocomplete(c_fab, lista_fab_os, somente_lista=False)
        tk.Label(jan_o, text="Modelo do Instrumento:").pack(pady=5)
        c_mo = ttk.Combobox(jan_o, width=27); c_mo.pack()
        cursor.execute("SELECT nome_inst || ' ' || modelo FROM modelos")
        c_mo['values'] = [r[0] for r in cursor.fetchall()]; conn.close()
        configurar_autocomplete(c_mo, c_mo['values'], somente_lista=False)
        tk.Label(jan_o, text="Número de Série:").pack(pady=5)
        e_s = tk.Entry(jan_o, width=30); e_s.pack()
        tk.Label(jan_o, text="Identificação adicional:").pack(pady=5)
        e_id = tk.Entry(jan_o, width=30); e_id.pack()
        tk.Label(jan_o, text="Número de Patrimônio:").pack(pady=5)
        e_p = tk.Entry(jan_o, width=30); e_p.pack()

        if id_os:
            conn = sqlite3.connect("sistema_gmf.db"); cursor = conn.cursor()
            cursor.execute("""SELECT num_os, modelo_ref, num_serie, identificacao, patrimonio, COALESCE(fabricante,'')
                              FROM ordens_servico WHERE id=?""", (id_os,))
            d = cursor.fetchone(); conn.close()
            if d: e_o.insert(0, d[0]); c_mo.set(d[1]); e_s.insert(0, d[2]); e_id.insert(0, d[3]); e_p.insert(0, d[4]); c_fab.set(d[5])
        else:
            e_o.insert(0, gerar_proximo_numero("ordens_servico", "num_os", "/"))

        def gravar():
            salvar_orcamento_pai()
            conn = sqlite3.connect("sistema_gmf.db"); cursor = conn.cursor()
            if id_os:
                cursor.execute("""UPDATE ordens_servico SET num_os=?, modelo_ref=?, num_serie=?,
                                  identificacao=?, patrimonio=?, fabricante=? WHERE id=?""",
                               (e_o.get(), c_mo.get(), e_s.get(), e_id.get(), e_p.get(), c_fab.get(), id_os))
            else:
                cursor.execute("""INSERT INTO ordens_servico
                                  (id_orcamento, num_os, modelo_ref, num_serie, identificacao, patrimonio, fabricante)
                                  VALUES (?,?,?,?,?,?,?)""",
                               (id_orc_atual[0], e_o.get(), c_mo.get(), e_s.get(), e_id.get(), e_p.get(), c_fab.get()))
            conn.commit(); conn.close(); jan_o.destroy(); carregar_os()
        tk.Button(jan_o, text="GRAVAR OS", command=gravar,
                  bg="#28a745", fg="white", font=("Arial", 10, "bold")).pack(pady=15)

    f_tab_os = tk.Frame(f_os); f_tab_os.pack(side="left", fill="both", expand=True)
    tab_os = ttk.Treeview(f_tab_os,
                          columns=("ID", "Número de Os", "Fabricante", "Modelo", "Número de Série",
                                   "Identificação adicional", "Número de Patrimônio"),
                          show="headings")
    for c in [("ID", 0), ("Número de Os", 100), ("Fabricante", 120), ("Modelo", 160), ("Número de Série", 120),
              ("Identificação adicional", 140), ("Número de Patrimônio", 120)]:
        tab_os.heading(c[0], text=c[0], command=lambda _c=c[0]: ajustar_coluna_auto(tab_os, _c))
        tab_os.column(c[0], width=c[1], stretch=tk.NO if c[0] == "ID" else tk.YES)
    tab_os.pack(fill="both", expand=True)
    tab_os.bind("<Double-1>", lambda e: add_os(tab_os.item(tab_os.selection())['values'][0]) if tab_os.selection() else None)
    lbl_total_os = tk.Label(f_tab_os, text="Total de OS: 0", font=("Arial", 9, "bold"), anchor="e")
    lbl_total_os.pack(fill="x", pady=2)

    f_b_os = tk.Frame(f_os); f_b_os.pack(side="right", fill="y", padx=5)
    tk.Button(f_b_os, text="+", bg="#28a745", fg="white", font=("Arial", 12, "bold"), width=3,
              command=add_os).pack(pady=2)

    def excluir_os():
        sel = tab_os.selection()
        if not sel: return
        id_del = tab_os.item(sel)['values'][0]
        conn = sqlite3.connect("sistema_gmf.db"); cursor = conn.cursor()
        cursor.execute("DELETE FROM ordens_servico WHERE id=?", (id_del,))
        conn.commit(); conn.close(); carregar_os()

    tk.Button(f_b_os, text="-", bg="#dc3545", fg="white", font=("Arial", 12, "bold"), width=3,
              command=excluir_os).pack(pady=2)
    tk.Button(f_b_os, text="✎", bg="#ffc107", font=("Arial", 12, "bold"), width=3,
              command=lambda: add_os(tab_os.item(tab_os.selection())['values'][0])).pack(pady=2)

    f_rodape_orc = tk.Frame(jan_detalhe); f_rodape_orc.pack(fill="x", padx=10, pady=8)
    tk.Button(f_rodape_orc, text="💾  SALVAR", bg="#28a745", fg="white",
              font=("Arial", 9, "bold"), width=14,
              command=lambda: [salvar_orcamento_pai(), jan_detalhe.destroy()]).pack(side="right")
    carregar_itens(); carregar_os()

def abrir_janela_orcamentos(pai=None):
    if pai is None:
        jan_lista = tk.Toplevel()
        jan_lista.title("Gestão de Orçamentos - GMF")
        jan_lista.geometry("900x500")
    else:
        for w in pai.winfo_children(): w.destroy()
        jan_lista = pai

    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Treeview.Heading", background="#4a90e2", foreground="white", font=("Arial", 10, "bold"))

    f_filtro = tk.LabelFrame(jan_lista, text=" Filtros de Busca ", padx=10, pady=10)
    f_filtro.pack(fill="x", padx=10, pady=10)
    tk.Label(f_filtro, text="Número:").grid(row=0, column=0, sticky="w")
    cb_n = ttk.Combobox(f_filtro, width=15); cb_n.grid(row=1, column=0, padx=5, pady=2)
    tk.Label(f_filtro, text="Cliente:").grid(row=0, column=1, sticky="w")
    cb_c = ttk.Combobox(f_filtro, width=30); cb_c.grid(row=1, column=1, padx=5, pady=2)
    tk.Label(f_filtro, text="Status:").grid(row=0, column=2, sticky="w")
    cb_s = ttk.Combobox(f_filtro,
                        values=["", "Aprovado", "Aguardando aprovação", "Não Aprovado", "Cancelado"],
                        width=20); cb_s.grid(row=1, column=2, padx=5, pady=2)
    def limpar_filtros_orc():
        cb_n.set(""); cb_c.set(""); cb_s.set("")
        atualizar_lista()
    tk.Button(f_filtro, text="LIMPAR", command=limpar_filtros_orc,
              bg="#6c757d", fg="white", font=("Arial", 9, "bold")).grid(row=1, column=3, padx=10)

    def carregar_opcoes_orc():
        conn = sqlite3.connect("sistema_gmf.db"); cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT num_orc FROM orcamentos ORDER BY num_orc")
        nums = [r[0] for r in cursor.fetchall()]
        cursor.execute("SELECT DISTINCT cliente FROM orcamentos ORDER BY cliente")
        clis = [r[0] for r in cursor.fetchall()]
        conn.close()
        return nums, clis

    def atualizar_lista(event=None):
        for i in tv.get_children(): tv.delete(i)
        conn = sqlite3.connect("sistema_gmf.db"); cursor = conn.cursor()
        cursor.execute("""SELECT o.id, o.num_orc, o.cliente, o.status,
                                 COALESCE(SUM(i.valor * COALESCE(i.quantidade,1)),0)
                          FROM orcamentos o
                          LEFT JOIN orc_itens i ON i.id_orcamento = o.id
                          WHERE o.num_orc LIKE ? AND o.cliente LIKE ? AND o.status LIKE ?
                          GROUP BY o.id""",
                       (f"%{cb_n.get()}%", f"%{cb_c.get()}%", f"%{cb_s.get()}%"))
        rows = cursor.fetchall()
        for r in rows:
            tv.insert("", tk.END, values=(r[1], r[2], r[3], f"R$ {r[4]:.2f}", r[0]))
        conn.close()
        lbl_total_orc.config(text=f"Total de orçamentos: {len(rows)}")
        nums_f, clis_f = carregar_opcoes_orc()
        cb_n['values'] = nums_f; cb_c['values'] = clis_f

    nums_orc, clis_orc = carregar_opcoes_orc()
    cb_n.config(state="readonly"); cb_n['values'] = nums_orc
    cb_c.config(state="readonly"); cb_c['values'] = clis_orc
    _buf_n = [""]; _buf_c = [""]
    def jump_orc(cb, buf, lista, event):
        ch = event.char
        if not ch or not ch.isprintable(): return
        buf[0] += ch.lower()
        matches = [v for v in lista if v.lower().startswith(buf[0])]
        if not matches:
            buf[0] = ch.lower()
            matches = [v for v in lista if v.lower().startswith(buf[0])]
        if matches:
            cb.set(matches[0]); cb.event_generate("<<ComboboxSelected>>")
        jan_lista.after(800, lambda: buf.__setitem__(0, ""))
    cb_n.bind("<KeyPress>", lambda e: jump_orc(cb_n, _buf_n, nums_orc, e))
    cb_c.bind("<KeyPress>", lambda e: jump_orc(cb_c, _buf_c, clis_orc, e))
    for w in [cb_n, cb_c]:
        w.bind("<<ComboboxSelected>>", atualizar_lista)
    cb_s.bind("<<ComboboxSelected>>", atualizar_lista)

    f_tab = tk.Frame(jan_lista); f_tab.pack(fill="both", expand=True, padx=10)
    tv = ttk.Treeview(f_tab, columns=("Número", "Cliente", "Status", "Valor Total", "ID"), show="headings")
    for c in [("Número", 120), ("Cliente", 320), ("Status", 150), ("Valor Total", 120), ("ID", 0)]:
        tv.heading(c[0], text=c[0], command=lambda _c=c[0]: ajustar_coluna_auto(tv, _c))
        tv.column(c[0], width=c[1], stretch=tk.NO if c[0] in ("Número", "Status", "Valor Total", "ID") else tk.YES)
    tv.pack(side="left", fill="both", expand=True)

    tv.bind("<Double-1>", lambda e: abrir_detalhes_orcamento(
        tv.item(tv.selection())['values'][4], atualizar_lista) if tv.selection() else None)

    f_btn = tk.Frame(f_tab); f_btn.pack(side="right", fill="y", padx=5)
    tk.Button(f_btn, text="+", bg="#28a745", fg="white", font=("Arial", 12, "bold"), width=3,
              command=lambda: abrir_detalhes_orcamento(None, atualizar_lista)).pack(pady=2)

    def excluir_orc():
        sel = tv.selection()
        if not sel: return
        id_del = tv.item(sel)['values'][4]
        conn = sqlite3.connect("sistema_gmf.db"); cursor = conn.cursor()
        cursor.execute("DELETE FROM orcamentos WHERE id=?", (id_del,))
        conn.commit(); conn.close(); atualizar_lista()

    tk.Button(f_btn, text="-", bg="#dc3545", fg="white", font=("Arial", 12, "bold"), width=3,
              command=excluir_orc).pack(pady=2)
    tk.Button(f_btn, text="✎", bg="#ffc107", font=("Arial", 12, "bold"), width=3,
              command=lambda: abrir_detalhes_orcamento(
                  tv.item(tv.selection())['values'][4], atualizar_lista) if tv.selection() else None
              ).pack(pady=2)

    f_rodape_orc_lista = tk.Frame(jan_lista, padx=10, pady=5)
    f_rodape_orc_lista.pack(fill="x", side="bottom")
    lbl_total_orc = tk.Label(f_rodape_orc_lista, text="Total de orçamentos: 0",
                             font=("Arial", 9, "bold"))
    lbl_total_orc.pack(side="right")

    atualizar_lista()


# ============================================================
# JANELA PRINCIPAL — MENU GMF
# ============================================================
iniciar_banco()
root = tk.Tk()
root.title("Sistema GMF - Gestão de Metrologia e Faturamento")
root.geometry("1100x650")
root.resizable(True, True)
root.minsize(800, 500)

# --- Painel esquerdo (menu) ---
f_menu = tk.Frame(root, bg="#2c3e50", width=220)
f_menu.pack(side="left", fill="y")
f_menu.pack_propagate(False)

tk.Label(f_menu, text="GMF", font=("Arial", 22, "bold"), bg="#2c3e50", fg="white").pack(pady=(30, 2))
tk.Label(f_menu, text="Gestão de Metrologia\ne Faturamento", font=("Arial", 8),
         bg="#2c3e50", fg="#aab7c4", justify="center").pack(pady=(0, 30))

tk.Frame(f_menu, bg="#3d5166", height=1).pack(fill="x", padx=15, pady=5)

# --- Separador vertical ---
tk.Frame(root, bg="#bdc3c7", width=1).pack(side="left", fill="y")

# --- Painel direito (conteúdo) ---
f_conteudo = tk.Frame(root, bg="#ecf0f1")
f_conteudo.pack(side="right", fill="both", expand=True)

# Tela de boas-vindas
def mostrar_boas_vindas():
    for w in f_conteudo.winfo_children(): w.destroy()
    f_bv = tk.Frame(f_conteudo, bg="#ecf0f1")
    f_bv.place(relx=0.5, rely=0.45, anchor="center")
    tk.Label(f_bv, text="Bem-vindo ao Sistema GMF",
             font=("Arial", 16, "bold"), bg="#ecf0f1", fg="#2c3e50").pack()
    tk.Label(f_bv, text="Selecione um módulo no menu ao lado para começar.",
             font=("Arial", 10), bg="#ecf0f1", fg="#7f8c8d").pack(pady=8)

mostrar_boas_vindas()

# Controle do botão ativo
btn_ativo = [None]
cor_inativa = "#34495e"
cores = {"clientes": "#28a745", "orcamentos": "#4a90e2", "instrumentos": "#6c757d"}

def criar_botao_menu(texto, chave, func):
    btn = tk.Button(f_menu, text=texto, bg=cor_inativa, fg="white",
                    font=("Arial", 10, "bold"), width=22, height=2,
                    bd=0, relief="flat", cursor="hand2")
    btn.pack(pady=4, padx=12)

    def ao_clicar():
        # Resetar todos os botões
        for b, c in botoes_menu:
            b.config(bg=cor_inativa)
        # Destacar o ativo
        btn.config(bg=cores[chave])
        btn_ativo[0] = chave
        func(f_conteudo)

    btn.config(command=ao_clicar)

    def on_enter(e):
        if btn_ativo[0] != chave:
            btn.config(bg="#3d5a74")
    def on_leave(e):
        if btn_ativo[0] != chave:
            btn.config(bg=cor_inativa)
        else:
            btn.config(bg=cores[chave])
    btn.bind("<Enter>", on_enter)
    btn.bind("<Leave>", on_leave)
    return btn

botoes_menu = []
botoes_menu.append((criar_botao_menu("👥  CLIENTES", "clientes", abrir_cadastro), "clientes"))
botoes_menu.append((criar_botao_menu("📋  ORÇAMENTOS", "orcamentos", abrir_janela_orcamentos), "orcamentos"))
botoes_menu.append((criar_botao_menu("📏  INSTRUMENTOS", "instrumentos", abrir_janela_modelos), "instrumentos"))

tk.Frame(f_menu, bg="#3d5166", height=1).pack(fill="x", padx=15, pady=15)
tk.Label(f_menu, text="v1.0", font=("Arial", 8), bg="#2c3e50", fg="#636e72").pack(side="bottom", pady=10)

root.mainloop()